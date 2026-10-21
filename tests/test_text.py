"""Exercise note safety without requiring a display or haltia-kit."""
import ast
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
namespace = dict(os=os, tempfile=tempfile, uuid=__import__('uuid'),
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

    def test_failed_trash_keeps_recent_and_editor(self):
        namespace['dialogs'].ask.return_value = False
        namespace['Gio'].File.new_for_path.return_value.trash.side_effect = RuntimeError()
        self.app.forget = Mock()
        self.app.drop_recent('note.txt', True)
        self.app.forget.assert_not_called()
        self.app.show_start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
