#!/usr/bin/env python3
# base: 2010-02
# license: WTFPLv2

from importlib import import_module
from pathlib import Path
import sys
import os

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
	QMainWindow, QListWidgetItem, QApplication, QAbstractItemView,
)
from PyQt5.uic import loadUiType

from . import dbtag
from .fullscreenviewer import ImageViewer


def load_ui_class(package, module_name, class_name):
	try:
		mod = import_module(f'.{module_name}_ui', package)
	except ImportError:
		mod = import_module(f'.', package)

		folder = Path(mod.__path__[0])
		path = folder.joinpath(f'{module_name}.ui')
		return loadUiType(str(path))[0]
	else:
		return getattr(mod, class_name)


Ui_MainWindow = load_ui_class('sittagger', 'mainwindow', 'MainWindow')


class Win(Ui_MainWindow, QMainWindow):
	def __init__(self, options):
		super(Win, self).__init__()
		super().setupUi(self)

		self.setWindowIcon(QIcon(QPixmap(
			str(Path(__file__).parent.with_name("sittagger.png"))
		)))

		self.db = dbtag.Db()
		self.db.open(options.db)
		self.db.do_migrations()
		self.rootPath = options.filespath

		self._init_dirchooser(options.target)
		self._init_tagchooser()
		self._init_imagelist()
		self._init_tabs()
		self.viewer = None

	def _init_dirchooser(self, folder):
		if folder.is_file():
			folder = folder.parent
		folder = str(folder)

		self.dirChooser.setRootPath(self.rootPath)
		self.dirChooser.selectionModel().currentChanged.connect(self.browseSelectedDir)
		self.dirChooser.selectPath(folder)
		self.dirChooser.openTo(folder)

	def _init_imagelist(self):
		self.imageList.itemSelectionChanged.connect(self._editTagsItems)
		self.imageList.itemActivated.connect(self._spawnViewerItem)
		self.imageList.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.imageList.pasteRequested.connect(self._onListPaste)

	def _init_tabs(self):
		self.tabWidget.currentChanged.connect(self._tabSelected)
		self.hSplitter.setStretchFactor(1, 1)

	def _init_tagchooser(self):
		self.tagChooser.setDb(self.db)
		self.tagChooser.changed.connect(self.browseSelectedTags)
		self.tagChooserFilter.setWidget(self.tagChooser)

		self.tagEditor.setDb(self.db)
		self.tagEditorFilter.setWidget(self.tagEditor)
		self.tagEditor.changedTags.connect(self.tagChooser.refreshTags)

	def editTags(self, path):
		self.tagEditor.setEnabled(True)
		self.tagEditor.setFile(path)

	def editTagsItems(self, paths):
		self.tagEditor.setEnabled(bool(paths))
		self.tagEditor.setFiles(paths)

	def spawnViewer(self, files, currentFile):
		viewer = ImageViewer(self.db, parent=self)
		viewer.spawn(files, currentFile)

	@Slot()
	def _editTagsItems(self):
		self.editTagsItems([qitem.getPath() for qitem in self.imageList.selectedItems()])

	@Slot(QListWidgetItem)
	def _spawnViewerItem(self, qitem):
		self.spawnViewer(self.imageList.getFiles(), qitem.getPath())

	@Slot()
	def browseSelectedDir(self):
		path = self.dirChooser.selectedPath()
		if not path:
			return

		self.setWindowTitle(str(path))

		files = [os.path.join(path, f) for f in os.listdir(path)]
		files = [f for f in files if os.path.isfile(f)]
		files.sort()
		self.imageList.setFiles(files)

	@Slot()
	def browseSelectedTags(self):
		self.setWindowTitle(' + '.join(self.tagChooser.selectedTags()))
		self.imageList.setFiles(self.tagChooser.matchingFiles())

	@Slot(int)
	def _tabSelected(self, idx):
		if idx == 0:
			self.browseSelectedDir()
		else:
			self.browseSelectedTags()

	def browsePath(self, path):
		self.imageList.setFiles(os.path.join(path, f) for f in os.listdir(path))


	@Slot()
	def _onListPaste(self):
		if self.tabWidget.currentIndex() != 0:
			return

		self.dirChooser.pasteFiles()


def xdg_config():
	return os.getenv('XDG_CONFIG_HOME', str(Path.home() / ".config"))


def parse_options(args):
	import argparse

	default_db = os.getenv('SITTAGGER_DATABASE') or xdg_config() + '/sit-tagger.sqlite'

	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--database', metavar='FILE', dest='db')
	parser.add_argument('-p', '--path', dest='filespath')
	parser.add_argument('target', nargs='?', default=Path.cwd(), type=Path)
	parser.set_defaults(filespath='/', db=default_db)
	opts = parser.parse_args(args)
	opts.target = opts.target.absolute()
	return opts


def main():
	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	app = QApplication(sys.argv)
	app.setApplicationDisplayName('SIT-Tagger')
	app.setApplicationName('SIT-Tagger')

	opts = parse_options(list(app.arguments())[1:])
	win = Win(opts)
	win.show()
	app.exec_()


if __name__ == '__main__':
	main()
