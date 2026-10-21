"""Exercise note safety without requiring a display or haltia-kit."""
import ast
from datetime import datetime
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


source = ast.parse((Path(__file__).resolve().parents[1] / 'haltia-text').read_text())
nodes = [node for node in source.body
         if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
for node in nodes:
    if isinstance(node, ast.ClassDef):
        node.bases = [ast.Name(id='object', ctx=ast.Load())]
namespace = dict(os=os, tempfile=tempfile, datetime=datetime,
                 GLib=types.SimpleNamespace(Error=RuntimeError,
                                            timeout_add=Mock(return_value=42),
                                            source_remove=Mock()),
                 Gio=Mock(), dialogs=Mock())
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
             'haltia-text', 'exec'), namespace)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = namespace['Text'].__new__(namespace['Text'])
        self.app.path = None
        self.app.dirty = True
        self.app.loading = False
        self.app.autosave_source = None
        self.app.win = Mock()
        self.app.update_title = Mock()
        self.app.remember = Mock()
        self.app.message = Mock()
        self.app.show_start = Mock()
        self.app.view = Mock()
        self.app.view.get_buffer().get_text.return_value = 'Привет\n'
        namespace['documents'] = lambda: self.folder.name
        namespace['dialogs'].reset_mock()
        namespace['GLib'].source_remove.reset_mock()

    def test_trash_requires_confirmation(self):
        path = Path(self.folder.name) / 'note.txt'
        path.write_text('keep')
        namespace['Gio'].File.new_for_path.return_value.trash.side_effect = RuntimeError()
        namespace['dialogs'].ask.return_value = False
        self.assertFalse(namespace['trash'](str(path), self.app.win))
        self.assertTrue(path.exists())
        namespace['dialogs'].ask.return_value = True
        self.assertTrue(namespace['trash'](str(path), self.app.win))
        self.assertFalse(path.exists())

    def test_unsaved_delete_can_be_cancelled(self):
        namespace['dialogs'].ask.return_value = False
        self.app.delete_current()
        self.app.show_start.assert_not_called()
        self.assertTrue(self.app.dirty)
        namespace['dialogs'].ask.return_value = True
        self.app.delete_current()
        self.app.show_start.assert_called_once()

    def test_typing_restarts_timer(self):
        self.app.on_changed(None)
        self.app.on_changed(None)
        namespace['GLib'].source_remove.assert_called_once_with(42)
        namespace['GLib'].timeout_add.assert_called_with(3000, self.app.autosave)

    def test_autosave_new_note(self):
        self.assertFalse(self.app.autosave())
        self.assertEqual(Path(self.app.path).read_text(), 'Привет\n')
        self.assertFalse(self.app.dirty)
        namespace['dialogs'].text.assert_not_called()

    def test_autosave_uses_readable_unique_names(self):
        clock = Mock()
        clock.now.return_value = datetime(2026, 10, 22, 14, 5)
        first = Path(self.folder.name) / 'Заметка 22 октября 14-05.txt'
        second = first.with_name('Заметка 22 октября 14-05 (2).txt')
        first.write_text('first')
        second.write_text('second')
        with patch.dict(namespace, datetime=clock):
            self.assertTrue(self.app.save(automatic=True))
        self.assertEqual(Path(self.app.path).name, 'Заметка 22 октября 14-05 (3).txt')
        self.assertEqual(first.read_text(), 'first')
        self.assertEqual(second.read_text(), 'second')

    def test_new_file_permissions(self):
        self.assertTrue(self.app.save(automatic=True))
        self.assertEqual(os.stat(self.app.path).st_mode & 0o7777, 0o644)

    def test_existing_file_permissions_are_preserved(self):
        path = Path(self.folder.name) / 'private.txt'
        path.write_text('original')
        path.chmod(0o640)
        self.app.path = str(path)
        self.assertTrue(self.app.save())
        self.assertEqual(path.stat().st_mode & 0o7777, 0o640)

    def test_close_and_hide_save(self):
        self.assertFalse(self.app.on_close())
        self.app.view.get_buffer().get_text.return_value = 'changed'
        self.app.dirty = True
        self.app.on_hide()
        self.assertEqual(Path(self.app.path).read_text(), 'changed')

    def test_failed_replace_preserves_original_and_dirty_buffer(self):
        path = Path(self.folder.name) / 'note.txt'
        path.write_text('original')
        self.app.path = str(path)
        with patch.object(os, 'replace', side_effect=OSError('failed')):
            self.assertFalse(self.app.save())
        self.assertEqual(path.read_text(), 'original')
        self.assertTrue(self.app.dirty)
        self.assertEqual(list(Path(self.folder.name).iterdir()), [path])

    def test_close_failure_can_be_cancelled(self):
        self.app.save = Mock(return_value=False)
        self.app.confirm = Mock(return_value=False)
        self.assertTrue(self.app.on_close())

    def test_hide_does_not_save_after_discarding_on_close(self):
        self.app.save = Mock(return_value=False)
        self.app.confirm = Mock(return_value=True)
        self.assertFalse(self.app.on_close())
        self.app.on_hide()
        self.app.save.assert_called_once_with(automatic=True)
        self.assertFalse(self.app.dirty)

    def test_failed_trash_keeps_recent_and_editor(self):
        namespace['dialogs'].ask.return_value = False
        namespace['Gio'].File.new_for_path.return_value.trash.side_effect = RuntimeError()
        self.app.forget = Mock()
        self.app.drop_recent('note.txt', True)
        self.app.forget.assert_not_called()
        self.app.show_start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
