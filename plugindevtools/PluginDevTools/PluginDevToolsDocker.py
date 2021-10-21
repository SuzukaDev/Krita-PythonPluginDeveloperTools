from krita import *
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg, uic
import sip
import pprint
import time
from contextlib import redirect_stdout
import io
import re


class PluginDevToolsDocker(DockWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Plugin Developer Tools")
       
        self.centralWidget = uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + '/DockerWidget.ui')
        
        self.setWidget(self.centralWidget)
        self.firstRun = True
        self.currentTab = None
        #self.tabChanged(None)
        self.centralWidget.tabWidget.setTabIcon( 0, Krita.instance().icon('pivot-point') )
        self.centralWidget.tabWidget.currentChanged.connect(self.tabChanged)

        

    
    def windowCreatedSetup(self):

        
        self.t = {}
        
        self.qwin = Krita.instance().activeWindow().qwindow()
        
        
        self.t['welcome'] = self.PluginDevToolsWelcome(self)
        self.t['inspector'] = self.PluginDevToolsInspector(self)
        self.t['selector'] = self.PluginDevToolsSelector(self)
        self.t['console'] = self.PluginDevToolsConsole(self)
        self.t['icons'] = self.PluginDevToolsIcons(self)
        self.t['actions'] = self.PluginDevToolsActions(self)
        self.t['kritaapi'] = self.PluginDevToolsKritaAPI(self)
        
        

        
            
    def tabChanged(self, idx):
        if idx is not None:
            if self.firstRun:
                self.firstRun = False
                self.windowCreatedSetup()

            if self.currentTab:    
                self.t[self.currentTab].unselected()
        self.currentTab = self.centralWidget.tabWidget.currentWidget().objectName().replace('Tab','')
        print ("ON", self.currentTab)
        self.t[self.currentTab].selected()
        

    def canvasChanged(self, canvas):
        pass


    class PluginDevToolsWelcome():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller

        def selected(self):
            pass
        
        def unselected(self):
            pass

    class PluginDevToolsKritaAPI():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.kritaapiTreeView = self.caller.centralWidget.kritaapiTreeView
            self.kritaapiModel = QStandardItemModel()

            self.proxyModel = QSortFilterProxyModel()

            self.proxyModel.setFilterCaseSensitivity( Qt.CaseInsensitive )
            self.proxyModel.setFilterKeyColumn(-1)
            self.proxyModel.setRecursiveFilteringEnabled(True)

            self.proxyModel.setSourceModel(self.kritaapiModel)
            self.kritaapiTreeView.setModel(self.proxyModel)
            
            self.kritaapiModel.setHorizontalHeaderLabels(['Method', 'Return Type', 'Description'])
            
            self.firstRun = True
            

            
            


        def selected(self):
            if self.firstRun:
                self.firstRun = False
                rootItem = self.kritaapiModel.invisibleRootItem()
                
                
                item = QStandardItem("Krita.instance()")
                
                rootItem.appendRow([
                    item,
                    QStandardItem(""),
                    QStandardItem("")
                ])
                
                metaDict = self.genMethodList( Krita.instance(), Krita.__dict__ )
                
                for k, prop in sorted(metaDict['methods'].items()):
                    item.appendRow([
                        QStandardItem(prop['rec'][0]),
                        QStandardItem(prop['rec'][2]),
                        QStandardItem("")
                    ])
                    


                for k in dir(krita):
                    if k.startswith('__'): continue
                    item = QStandardItem(k)
                    
                    classMeta = getattr(krita, k)
                    
                    rootItem.appendRow([
                        item,
                        QStandardItem( "" ),
                        QStandardItem("")
                    ])
                    
                    
                    
                    #if hasattr(className,'staticMetaObject'):
    
                    
                    metaDict = self.genMethodList( classMeta, classMeta.__dict__ )

                
                    for k, prop in sorted(metaDict['methods'].items()):
                        item.appendRow([
                            QStandardItem(prop['rec'][0]),
                            QStandardItem(prop['rec'][2]),
                            QStandardItem(prop['rec'][1])
                        ])
                        
                        
                    if hasattr(classMeta,'staticMetaObject'):
                        parentMetaClass = classMeta.staticMetaObject.superClass()
                        
                        if parentMetaClass and not parentMetaClass.className().startswith('Q') and not parentMetaClass.className().startswith('Kis'):
                            parentMeta = getattr(krita, parentMetaClass.className())
                            
                            parentItem = QStandardItem("Inherited from " + parentMetaClass.className() )
                            item.appendRow([
                                parentItem,
                                QStandardItem(""),
                                QStandardItem("")
                            ])
                            
                            metaDict2 = self.genMethodList( parentMeta, parentMeta.__dict__ )
                            
                            for k2, prop2 in sorted(metaDict2['methods'].items()):
                                parentItem.appendRow([
                                    QStandardItem(prop2['rec'][0]),
                                    QStandardItem(prop2['rec'][2]),
                                    QStandardItem(prop2['rec'][1])
                                ])
                
                self.caller.centralWidget.kritaapiFilter.textChanged.connect(self.searchTreeFilter)
                self.kritaapiTreeView.expandAll()   
        
        def unselected(self):
            pass

        def searchTreeFilter(self, text):
            self.proxyModel.setFilterFixedString(text)
            self.kritaapiTreeView.expandAll()
            
            indexes = self.kritaapiTreeView.selectionModel().selectedIndexes()
                       
            if indexes:
                self.kritaapiTreeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)


        def genMethodList(self, obj, meta ):
            metaDict = { 'properties':{}, 'methods':{} }
            metaDict2 = { 'properties':{}, 'methods':{} }
            
            if hasattr(obj,'staticMetaObject'):
                metaDict2 = self.genMethodList2(obj, obj.staticMetaObject)
             
            for key in meta.keys():
                if not key.startswith('__'):
                    doc = getattr(obj,key).__doc__
                    
                    if doc:
                        propName = doc.split(' -> ')
                        if '(self' not in propName[0]:
                            propName[0] = "" + "." + propName[0]
                        else:
                            propName[0] = propName[0].replace('(self, ','(').replace('(self','(')
                        
                        propName2 = ''
                        
                        if key in metaDict2['methods']:
                            #print ("FOUND", key)
                            propName2 = metaDict2['methods'][key]['rec'][0]
                        
                        metaDict['methods'][propName[0]]={ 'class': '', 'type':8, 'name': propName, 'rec':[ propName[0], propName2, (propName[1] if len(propName) == 2 else 'void')  ] }
                
            return metaDict
        
        def genMethodList2(self, obj, meta):
            
            metaDict = { 'properties':{}, 'methods':{}, 'classes':{} }
        
            for i in range(meta.propertyOffset(), meta.propertyCount(), 1 ):
                prop = meta.property(i)
                propName = prop.name()
                
                propName = propName[0].lower() + propName[1:]
                
                if propName not in metaDict['properties']:
                    #print ("PROP", propName, dir(obj) )
                    propType = prop.typeName()
                    propValue = pprint.pformat( getattr(obj, propName) )
                    
                    className = ''#type(obj).__name__
                    

                        
                    metaDict['properties'][propName]={ 'class': className, 'type':9, 'name': propName, 'rec':[ propName, propType, propValue ] }
            
            for i in range(meta.methodOffset(), meta.methodCount(), 1 ):
                meth = meta.method(i)
                pnames = meth.parameterNames()
                ptypes = meth.parameterTypes()
                className = None
                
                methName = str(meth.name(), 'utf-8') + "(" + str(b','.join( [ ptypes[i]+b" "+pnames[i] for i in range(0,meth.parameterCount()) ] ), 'utf-8') + ")"
                if methName not in metaDict['methods']:
                    methType = self.caller.t['inspector'].METHOD_ACCESS[int(meth.access())] + " " + self.caller.t['inspector'].METHOD_TYPES[int(meth.methodType())]
                    
                    className = ''#type(obj).__name__
                    
                    methShortName = str(meth.name(), 'utf-8')
                    if methShortName in metaDict['methods']:
                        metaDict['methods'][methShortName]['rec'][0] += "\n" + methName
                    else:    
                        metaDict['methods'][methShortName]={ 'class': className, 'type':0, 'name': methShortName, 'rec':[ methName, methType, meth.typeName() ] }
                    #>>metaDict['methods'][methName]={ 'class': className, 'type':0, 'name': str(meth.name(), 'utf-8'), 'rec':[ methName, methType, meth.typeName() ] }

            return metaDict

    class PluginDevToolsConsole():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.historyTreeView = self.caller.centralWidget.consoleOutputBrowser
            self.historyModel = QStandardItemModel()

            self.proxyModel = QSortFilterProxyModel()

            self.proxyModel.setSourceModel(self.historyModel)
            self.historyTreeView.setModel(self.proxyModel)
            
            self.textEdit = self.caller.centralWidget.consoleInputTextEdit
            
            
            
            self.textEditFilter = self.textEditFilterClass(self)
            self.textEdit.installEventFilter(self.textEditFilter)
            
            self.firstRun = True

        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                
                
                
        
        def unselected(self):
            pass
        
        
        def executeCode(self):
            script = self.textEdit.toPlainText()
            rootItem = QStandardItem( script )
            self.historyModel.appendRow( rootItem )
            
            
            f = io.StringIO()
            with redirect_stdout(f):
            
                try:
                    code = compile(script, '<string>', 'exec')
                    exec(code, {'__name__': '__main__'})
                except SystemExit:
                    self.historyModel.clear()
                    self.textEdit.setPlainText("")
                    return
                    # user typed quit() or exit()
                except Exception:
                    type_, value_, traceback_ = sys.exc_info()
                    if type_ == SyntaxError:
                        errorMessage = "%s\n%s" % (value_.text.rstrip(), " " * (value_.offset - 1) + "^")
                        # rstrip to remove trailing \n, output needs to be fixed width font for the ^ to align correctly
                        errorText = "Syntax Error on line %s" % value_.lineno
                    elif type_ == IndentationError:
                        # (no offset is provided for an IndentationError
                        errorMessage = value_.text.rstrip()
                        errorText = "Unexpected Indent on line %s" % value_.lineno
                    else:
                        errorText = traceback.format_exception_only(type_, value_)[0]
                        format_string = "In file: {0}\nIn function: {2} at line: {1}. Line with error:\n{3}"
                        tbList = traceback.extract_tb(traceback_)
                        tb = tbList[-1]
                        errorMessage = format_string.format(*tb)
                    item = QStandardItem( "%s\n%s" % (errorText, errorMessage) )
                    item.setForeground(QBrush(QColor('#990000')))
                    rootItem.appendRow( item )

            
            item = QStandardItem( f.getvalue() )
            item.setForeground(QBrush(QColor('#000099')))
            rootItem.appendRow( item )
            
            self.historyTreeView.expand(self.proxyModel.mapFromSource(rootItem.index()));

            self.historyTreeView.scrollToBottom()

            
            self.textEdit.setPlainText("")

        class textEditFilterClass(QWidget):
            def __init__(self, caller, parent=None):
                super().__init__()
                self.caller = caller
            
            def eventFilter(self, obj, event):
                etype = event.type()
                if etype == 6 and event.key() == Qt.Key_Return and QApplication.keyboardModifiers() != Qt.ShiftModifier:
                    self.caller.executeCode()
                    #print ("ENTER!")
                    return True
                return False

    class PluginDevToolsIcons():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            

            self.page = self.caller.centralWidget.iconsTab
            
            self.listView = self.caller.centralWidget.iconsListView
            
            self.listView.setGridSize( QSize(128,128) )
            
            self.listModel = QStandardItemModel()
            self.proxyModel = QSortFilterProxyModel()

            self.proxyModel.setSourceModel(self.listModel)
            self.listView.setModel(self.proxyModel)
            
            self.proxyModel.setFilterCaseSensitivity( Qt.CaseInsensitive )
            
            self.listView.clicked.connect(self.iconClicked)
            
            self.firstRun = False



        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                
                self.loadIconList()

                self.iconsGroup = QButtonGroup(self.page)
                self.iconsGroup.setExclusive(False)
                
                self.iconsGroup.addButton( self.caller.centralWidget.boolIconsKrita )
                self.iconsGroup.addButton( self.caller.centralWidget.boolIconsKritaExtra )
                self.iconsGroup.addButton( self.caller.centralWidget.boolIconsTheme )

                self.iconsGroup.buttonToggled.connect(self.loadIconList)
                self.caller.centralWidget.iconsFilter.textChanged.connect(self.searchFilter)
        
        def unselected(self):
            pass
        
        def loadIconList(self):
            iconDict = {}
            
            self.listModel.clear()
            
            iconFormats = ["*.svg","*.svgz","*.svz","*.png"]
            
            if self.caller.centralWidget.boolIconsKrita.isChecked():
                iconList = QDir(":/pics/").entryList(iconFormats, QDir.Files)
                iconList += QDir(":/").entryList(iconFormats, QDir.Files)
                
                for iconName in iconList:
                    name = iconName.split('_',1)
                    if any(iconSize == name[0] for iconSize in [ '16', '22', '24', '32', '48', '64', '128', '256', '512', '1048' ]):
                        iconName = name[1]
                        
                    name = iconName.split('_',1)
                    if any(iconSize == name[0] for iconSize in [ 'light', 'dark' ]):
                        iconName = name[1]
                        
                    name = iconName.split('.')
                    iconName = name[0]
                    iconDict[iconName]={}
                
            if self.caller.centralWidget.boolIconsKritaExtra.isChecked():
                iconList = QDir(":/icons/").entryList(iconFormats, QDir.Files)
                #iconList += QDir(":/images/").entryList(iconFormats, QDir.Files)

                for iconName in iconList:
                    name = iconName.split('.')
                    iconName = name[0]
                    iconDict[iconName]={}


            if self.caller.centralWidget.boolIconsTheme.isChecked():
                with open( os.path.dirname(os.path.realpath(__file__)) + '/ThemeIcons.txt' ) as f:
                    for iconName in f.readlines():
                        iconDict[iconName.rstrip()]={}

            
            for iconName, iconInfo in sorted(iconDict.items()):
                    item = QStandardItem( Krita.instance().icon(iconName), iconName )
                    
                    self.listModel.appendRow( item )
        
        
        def searchFilter(self, text):
            self.proxyModel.setFilterFixedString(text)


        def iconClicked(self, rec):
            self.caller.centralWidget.consoleInputTextEdit.setText("Krita.instance().icon('"+ self.proxyModel.index( rec.row(), 0 ).data() +"')")
            self.caller.centralWidget.tabWidget.setCurrentIndex(2)

    class PluginDevToolsActions():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            
            self.tableView = caller.centralWidget.actionsTableView
            
            self.tableModel = QStandardItemModel()
            self.proxyModel = QSortFilterProxyModel()
            self.tableModel.setHorizontalHeaderLabels(['Name', 'Description'])

            self.proxyModel.setSourceModel(self.tableModel)
            self.tableView.setModel(self.proxyModel)
            
            self.proxyModel.setFilterCaseSensitivity( Qt.CaseInsensitive )
            self.proxyModel.setFilterKeyColumn(-1)
            
            self.tableView.doubleClicked.connect(self.actionClicked)
            

            self.firstRun = False



        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                
                parentItem = self.tableModel.invisibleRootItem()
                
                for action in  Krita.instance().actions():
                    parentItem.appendRow([
                        QStandardItem( action.objectName() ), 
                        QStandardItem( action.toolTip() )
                    ])
                    #print ( action.objectName(), action.toolTip() )
                self.caller.centralWidget.actionsFilter.textChanged.connect(self.searchFilter)
        
        def unselected(self):
            pass
        
        def searchFilter(self, text):
            self.proxyModel.setFilterFixedString(text)

        def actionClicked(self, rec):
            self.caller.centralWidget.consoleInputTextEdit.setText("Krita.instance().action('"+ self.proxyModel.index( rec.row(), 0 ).data() +"').trigger()")
            self.caller.centralWidget.tabWidget.setCurrentIndex(2)
            #print ( "REC!", self.tableModel.index( rec.row(), 0 ).data() )

    class PluginDevToolsSelector():
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.windowFilter = self.windowFilterClass(self)
            
            self.selectorOutput = caller.centralWidget.selectorOutputLabel
            
            self.currentWidget = None
            self.currentWindow = None
            
            
            
            self.useStyleSheet = "*[DevToolsHoverWithSelector='true'] { background-color: rgba(0, 0, 155, 50); border: 1px solid #000080; }"
            self.useStyleSheet = None
            
            #self.caller.qwin.setStyleSheet( self.caller.qwin.styleSheet() + '*[DevToolsHoverWithSelector="true"] { background-color: rgba(0, 0, 155, 50); border: 1px solid #000080; }' )
            self.createSelector(self.caller.qwin)
            
        def createSelector(self, window):
            #print ("create selector!")
            selectorWidget = QWidget(window)
            selectorWidget.setObjectName("DevToolsSelectorWidget")
            #selectorWidget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
            selectorWidget.setWindowFlags(Qt.WindowTransparentForInput)
            selectorWidget.setAttribute( Qt.WA_TransparentForMouseEvents )
            selectorWidget.setVisible(False)
            selectorWidget.setStyleSheet("background-color: rgba(0, 0, 155, 50); border: 1px solid #000080;")
            #print ("selector id", selectorWidget)
            self.selectorWidget = selectorWidget
            
        def selected(self):
            self.startSampling(QtWidgets.qApp.activeWindow())    

        def unselected(self):
            self.stopSampling()    
            
        def startSampling(self, window):
            self.currentWindow = window
            #>winStyle = window.styleSheet()
            #>if "DevToolsHoverWithSelector=" not in winStyle:
            #>    window.setStyleSheet( winStyle + '*[DevToolsHoverWithSelector="true"] { background-color: #000000; border: 3px solid #FF0000; color: #FF0000 }' )
            QtWidgets.qApp.focusChanged.connect(self.focusItem)
            QtWidgets.qApp.installEventFilter(self.windowFilter)
            #>>>window.installEventFilter(self.windowFilter)
        
        def focusItem(self):
            #if self.currentWindow is not QApplication.activePopupWidget():
            #    print ("POPUP CHANGE!")
            win = QtWidgets.qApp.activeWindow()
            if self.currentWindow is not win:
                if win:
                    self.selectorWidget.setVisible(False)
                    wid = win.findChild(QWidget, "DevToolsSelectorWidget", Qt.FindDirectChildrenOnly)
                    if wid:
                        self.selectorWidget = wid
                    else:
                        self.createSelector(win)
                        # event filter never happens
                    self.currentWindow = win
                #print ("FOCUS CHANGED!", win, QApplication.activeModalWidget(), QApplication.activePopupWidget())

        def stopSampling(self, localCall = True):
            if self.currentWindow:
                if localCall:
                    QtWidgets.qApp.focusChanged.disconnect(self.focusItem)
                    QtWidgets.qApp.installEventFilter(self.windowFilter)
                #??self.currentWindow.removeEventFilter(self.windowFilter)
                self.currentWindow = None
            self.selectorWidget.setVisible(False)
                
            if self.currentWidget:
                if self.useStyleSheet:
                    self.currentWidget.setProperty('DevToolsHoverWithSelector', False)
                    self.currentWidget.setStyleSheet(self.currentWidget.styleSheet().replace(self.useStyleSheet,'') )
                #>>self.caller.t['inspector'].selectItemByRef(self.currentWidget)
                if localCall:
                    self.caller.centralWidget.selectorOutputLabel.setText("None")
                    self.caller.t['inspector'].loadItemInfo(self.currentWidget)
                self.currentWidget = None
                
        def finishedSampling(self):
            self.caller.centralWidget.tabWidget.setCurrentIndex(1)
            
        def findAncestor(self, ancestor, obj):
            parent = obj.parent()
            while True:
                if not parent:
                    return False
                elif ancestor is parent:
                    return True
                obj = parent
                parent = obj.parent()
                
        def setCurrentSelector(self, obj, localCall = True):
            if obj and obj is not self.currentWidget and self.findAncestor(self.currentWindow,obj):
                self.selectorWidget.setVisible(True)

                if self.useStyleSheet:
                    if self.currentWidget:
                        self.currentWidget.setProperty('DevToolsHoverWithSelector', False)
                        self.currentWidget.setStyleSheet(self.currentWidget.styleSheet().replace(self.useStyleSheet,""))
                    obj.setProperty('DevToolsHoverWithSelector', True)
                    obj.setStyleSheet(obj.styleSheet() + self.useStyleSheet)
                    obj.update()
                
                rect = obj.geometry()
                pos = obj.mapTo(self.currentWindow, QPoint(0,0) )
                rect.moveTo(pos)
                
                self.selectorWidget.setGeometry( rect )
                #obj.mapToGlobal(widgetRect.topLeft())
                
                
                #print (obj.property('DevToolsHoverWithSelector') )
                self.currentWidget = obj
                if localCall: self.caller.centralWidget.selectorOutputLabel.setText("[" + type(obj).__name__ + "] " + obj.objectName())
            
            
        class windowFilterClass(QWidget):
            def __init__(self, caller, parent=None):
                super().__init__()
                self.caller = caller
            
            def eventFilter(self, obj, event):
                etype = event.type()
                
                if etype == 129 or (etype == 6 and event.key() == Qt.Key_Shift):
                    if etype == 6 and event.key() == Qt.Key_Shift:
                        win = QtWidgets.qApp.activeWindow()
                        self.caller.selectorWidget=win.findChild(QWidget, "DevToolsSelectorWidget", Qt.FindDirectChildrenOnly)
                    
                    if QApplication.keyboardModifiers() == Qt.ShiftModifier:
                        pos = QCursor.pos()
                        onWidget = QApplication.widgetAt(pos)
                        self.caller.setCurrentSelector(onWidget)
                elif etype == 7 and event.key() == Qt.Key_Shift and self.caller.currentWidget:
                        self.caller.finishedSampling()
                       

                #print (obj, event.type())
                return False


    class PluginDevToolsInspector():
        METHOD_TYPES = [ 'Method', 'Signal', 'Slot', 'Constructor' ]
        METHOD_ACCESS = [ 'Private', 'Protected', 'Public' ]
        
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.currentWidget = None
            
            self.treeView = caller.centralWidget.inspectorTreeView
            self.tableView = caller.centralWidget.inspectorTableView
            
            self.treeView.setIndentation(10)
            
            self.treeModel = QStandardItemModel()
            self.proxyTreeModel = QSortFilterProxyModel()
            self.proxyTreeModel.setFilterCaseSensitivity( Qt.CaseInsensitive )
            self.proxyTreeModel.setRecursiveFilteringEnabled(True)
            self.proxyTreeModel.setFilterKeyColumn(-1)
            self.treeModel.setHorizontalHeaderLabels(['Class', 'Name', 'Meta Class', 'From', 'Text/Value'])

            self.proxyTreeModel.setSourceModel(self.treeModel)
            self.treeView.setModel(self.proxyTreeModel)
            
            self.treeSelectModel = self.treeView.selectionModel()
            
            self.tableModel = QStandardItemModel()
            self.proxyTableModel = QSortFilterProxyModel()
            self.tableModel.setHorizontalHeaderLabels(['Name', "Type", 'Value'])

            self.proxyTableModel.setSourceModel(self.tableModel)
            self.tableView.setModel(self.proxyTableModel)
            
            self.treeSelectModel.selectionChanged.connect(self.itemSelectionChanged)
            
            
            
            self.caller.centralWidget.inspectorRefreshBtn.setIcon( Krita.instance().icon('view-refresh') )
            self.caller.centralWidget.inspectorParentBtn.setIcon( Krita.instance().icon('arrow-up') )
            self.caller.centralWidget.inspectorCodeBtn.setIcon( Krita.instance().icon('document-print-preview') )
            self.caller.centralWidget.inspectorObjDocsBtn.setIcon( Krita.instance().icon('system-help') )
            self.caller.centralWidget.inspectorSelectorBtn.setIcon( Krita.instance().icon('pivot-point') )
            
            
            self.caller.centralWidget.inspectorObjDocsBtn.clicked.connect(self.getObjDocs)
            self.caller.centralWidget.inspectorPropDocsBtn.clicked.connect(self.getPropDocs)
            self.caller.centralWidget.inspectorCodeBtn.clicked.connect(self.getCode)
            self.caller.centralWidget.inspectorParentBtn.clicked.connect(self.getParent)
            
            self.caller.centralWidget.inspectorRefreshBtn.clicked.connect(self.refreshItems)
            
            self.caller.centralWidget.inspectorSelectorBtn.pressed.connect(self.showCurrentWidget)
            self.caller.centralWidget.inspectorSelectorBtn.released.connect(self.hideCurrentWidget)
            

                    
            self.caller.centralWidget.inspectorFilter.textChanged.connect(self.searchTreeFilter)
            self.firstRun = False

        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                for win in QApplication.instance().topLevelWidgets():
                    if isinstance(win, QMainWindow):
                        self.loadTreeItems(win, 0, 'topLevelWidgets')
        
        def unselected(self):
            pass
        
        def showCurrentWidget(self):
            #print ("show current!", self.currentWidget)
            self.caller.t['selector'].currentWindow = win = QtWidgets.qApp.activeWindow()
            self.caller.t['selector'].selectorWidget=win.findChild(QWidget, "DevToolsSelectorWidget", Qt.FindDirectChildrenOnly)
            self.caller.t['selector'].setCurrentSelector(self.currentWidget, False)
            
            
        def hideCurrentWidget(self):
            self.caller.t['selector'].stopSampling(False)
        
        def refreshItems(self):
            self.caller.centralWidget.inspectorFilter.setText("")
            self.treeModel.clear()
            self.treeModel.setHorizontalHeaderLabels(['Class', 'Name', 'Meta Class', 'From', 'Text/Value'])
            
            for win in QApplication.instance().topLevelWidgets():
                if isinstance(win, QMainWindow):
                    self.loadTreeItems(win, 0, 'topLevelWidgets')
            if self.currentWidget:
                self.loadItemInfo( self.currentWidget )
        
        def getObjDocs(self):
            if self.currentWidget:
                url = "https://doc.qt.io/qt-5.12/" + type(self.currentWidget).__name__ + ".html"
            
                QDesktopServices.openUrl(QUrl(url))

        def getPropDocs(self):
            index = self.tableView.currentIndex()
            
            if self.currentWidget and index:
                prop = self.tableView.model().index(index.row(), 0).data(101)
                if prop:
                    url = "https://doc.qt.io/qt-5.12/" + prop['class'] + ".html#" + prop['name']
                
                    if prop['type'] == 9:
                        url += "-prop"
            
                    #print( "DT", self.tableView.model().index(index.row(), 1).data(101) )
                    QDesktopServices.openUrl(QUrl(url))
        
        def getCode(self):
            obj = self.currentWidget
            
            lastNamed = None
            docker = None
            mdi = False
            path = []
            
            while True:
                path.append(obj)
                
                if obj.metaObject().className() == "QDockWidget":
                    if obj.parent() and obj.parent().className() == "QMainWindow":
                        docker = obj.objectName()
                elif obj.metaObject().className() == "QMdiArea":
                    mdi = True
                
                if obj.objectName() and not lastNamed:
                    lastNamed = obj
                
                obj=obj.parent()
                if not obj:
                    break
            
            

            onWidget = None
            
            if docker:
                codeBase = "from krita import *\n\nqdock = next((w for w in Krita.instance().dockers() if w.objectName() == '"+ docker +"'), None)\n"
                onWidget = "qdock"
                #codeBase = """qdock = None
                #for widget in Krita.instance().dockers():
                #    if widget.objectName() == '"""+ docker +"""':
                #        qdock = widget
                #        break
                #"""
            else:
                codeBase = "from krita import *\n\nqwin = Krita.instance().activeWindow().qwindow()\n"
                onWidget = "qwin"
                

                
            
            if self.currentWidget.objectName():
                codeBase += "obj = "+onWidget+".findChild("+ type(self.currentWidget).__name__ +",'"+ self.currentWidget.objectName() +"')\n"
            elif path:
                codeBase += "pobj = "+onWidget+".findChild("+ type(lastNamed).__name__ +",'"+ lastNamed.objectName() +"')\n"
                onWidget = "pobj"
                
                backFill = False
                
                for item in path.reverse():
                    if item is lastNamed:
                        if len(lastNamed.findChildren(type(self.currentWidget).__name__)) == 1:
                            codeBase += "obj = "+onWidget+".findChild("+ type(self.currentWidget).__name__ +")\n"
                        else:
                            backFill = True
                            codeBase += "# TODO "+type(item).__name__ + ""
                    elif backFill:
                        codeBase += " > "+type(item).__name__ +""
                
                
            #print ("PATH", path, codeBase)
                
                
            
            self.caller.centralWidget.consoleInputTextEdit.setText(codeBase)
            self.caller.centralWidget.tabWidget.setCurrentIndex(2)
        
        def getParent(self):
            if self.currentWidget:
                parent = self.currentWidget.parent()
                if parent:
                    self.loadItemInfo( parent )
        
        def searchTreeFilter(self, text):
            if len(text) >= 3:
                self.proxyTreeModel.setFilterFixedString(text)
                self.treeView.expandAll()
            else:
                self.treeView.collapseAll()
                self.proxyTreeModel.setFilterFixedString("")
                
            #self.proxyTreeModel.setFilterWildcard("*{}*".format(text))
            
            indexes = self.treeView.selectionModel().selectedIndexes()
                       
            if indexes:
                self.treeView.expand(self.proxyTreeModel.mapFromSource( indexes[0] ))
                self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)
                self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)

        
        def selectItemByRef(self, obj):
            idx = self.treeModel.match( self.treeModel.index(0,0) , 101, obj, 1, Qt.MatchRecursive )
            if idx:
                print ( idx[0].row() )
            
                #>>self.treeSelectModel.select(idx[0], self.treeSelectModel.Select | self.treeSelectModel.Rows )
        
        def itemSelectionChanged(self, new, old):
            indexes = new.indexes()
            if indexes:
                self.loadItemInfo( indexes[0].data(101) )
        
        def loadItemInfo(self, obj):
            if sip.isdeleted(obj): return
        
            self.currentWidget = obj
        
            self.tableModel.clear()
            self.tableModel.setHorizontalHeaderLabels(['Name', "Type", 'Value'])

            parentItem = self.tableModel.invisibleRootItem()

            metaDict = { 'properties':{}, 'methods':{} }
            
            meta = obj.metaObject()
            
            parentItem.appendRow([
                self.subheaderItem("Object"),
                self.subheaderItem(""),
                self.subheaderItem("")
            ])
            
            parentItem.appendRow([
                QStandardItem( "Name" ),
                QStandardItem( "" ),
                QStandardItem( obj.objectName() ),
            ])

            parentItem.appendRow([
                QStandardItem( "Class" ),
                QStandardItem( "" ),
                QStandardItem( type(obj).__name__ ),
            ])            
            
            parentItem.appendRow([
                QStandardItem( "Meta Class" ),
                QStandardItem( "" ),
                QStandardItem( meta.className() ),
            ])
            
            if obj.parent():
                parentItem.appendRow([
                    QStandardItem( "Parent" ),
                    QStandardItem( "" ),
                    QStandardItem( type(obj.parent()).__name__ + " " + obj.parent().objectName() ),
                ])
            
            inheritsFrom = []
            

            while True:
                for i in range(meta.propertyOffset(), meta.propertyCount(), 1 ):
                    prop = meta.property(i)
                    propName = prop.name()
                    if propName not in metaDict['properties']:
                        propType = prop.typeName()
                        propValue = pprint.pformat( obj.property(prop.name()) )
                        className = None
                        
                        if inheritsFrom:
                            propType = propType + " [from "+meta.className()+"]"
                            className = meta.className()
                        else:
                            className = type(obj).__name__
                            
                        metaDict['properties'][propName]={ 'class': meta.className(), 'type':9, 'name': propName, 'rec':[ propName, propType, propValue ] }
                
                for i in range(meta.methodOffset(), meta.methodCount(), 1 ):
                    meth = meta.method(i)
                    pnames = meth.parameterNames()
                    ptypes = meth.parameterTypes()
                    className = None
                    
                    methName = str(meth.name(), 'utf-8') + "(" + str(b','.join( [ ptypes[i]+b" "+pnames[i] for i in range(0,meth.parameterCount()) ] ), 'utf-8') + ")"
                    if methName not in metaDict['methods']:
                        methType = self.METHOD_ACCESS[int(meth.access())] + " " + self.METHOD_TYPES[int(meth.methodType())]
                        
                        if inheritsFrom:
                            methType = methType + " [from "+meta.className()+"]"
                            className = meta.className()
                        else:
                            className = type(obj).__name__
                        
                        metaDict['methods'][methName]={ 'class': meta.className(), 'type':0, 'name': str(meth.name(), 'utf-8'), 'rec':[ methName, methType, meth.typeName() ] }
                
               
                meta = meta.superClass()
                if meta:
                    inheritsFrom.append(meta.className())
                else:
                    break


            

            parentItem.appendRow([
                QStandardItem( "Inherits From" ),
                QStandardItem( "" ),
                QStandardItem( ' > '.join(inheritsFrom) ),
            ])              

            parentItem.appendRow([
                self.subheaderItem("Properties"),
                self.subheaderItem(""),
                self.subheaderItem("")
            ])

            for k, prop in sorted(metaDict['properties'].items()):
                item = [
                   QStandardItem( prop['rec'][0] ),
                   QStandardItem( prop['rec'][1] ),
                   QStandardItem( prop['rec'][2] ),
                ]
                
                item[0].setData(prop, 101)
                
                parentItem.appendRow(item)
                
                
            parentItem.appendRow([
                self.subheaderItem("Methods"),
                self.subheaderItem(""),
                self.subheaderItem("")
            ])
            for k, meth in sorted(metaDict['methods'].items()):
                item = [
                    QStandardItem( meth['rec'][0] ),
                    QStandardItem( meth['rec'][1] ),
                    QStandardItem( meth['rec'][2] ),
                ]
                
                item[0].setData(meth, 101)
                
                parentItem.appendRow(item)
                
        def subheaderItem(self, text):
            objectHeader = QStandardItem(text)
            font = objectHeader.font()
            font.setBold(True)
            objectHeader.setFont( font )
            objectHeader.setColumnCount(1)
            objectHeader.setEnabled(False)
            
            return objectHeader
            
        def loadTreeItems(self, pObj, depth, objType, parentItem = None):
            #if objType == 'viewport' and pObj: print ("VIEWPORT!!", pObj.children())
            if parentItem is None:
                parentItem = self.treeModel.invisibleRootItem()
                
                parentItem = self.setItem(pObj, parentItem, depth, objType)
                
                if isinstance(pObj, QMainWindow):
                    #idx = self.treeModel.indexFromItem(parentItem)
                    self.selectItemByRef(pObj)
                    #self.treeSelectModel.select(idx, self.treeSelectModel.Select | self.treeSelectModel.Rows )
                    #self.loadItemInfo(pObj)

                
                objType = 'children'
                depth = depth + 1
            
            for cObj in pObj.children():
                cObjType = objType
                if type(cObj).__name__ == 'QWidget' and cObj.objectName() == 'qt_scrollarea_viewport' and self.hasMethod(pObj,'viewport'):
                    cObjType = "viewport/children"
                
                item = self.setItem(cObj, parentItem, depth, cObjType)
                
                #if self.hasMethod(cObj,'viewport'):
                #    self.loadTreeItems(cObj.viewport(), depth + 1, 'viewport', item)
                    
                if self.hasMethod(cObj,'children') and type(cObj).__name__ != 'PluginDevToolsDocker':
                    #print ("CH", cObj.children())
                    
                    self.loadTreeItems(cObj, depth + 1, 'children', item)
                    
        def setItem(self, obj, parentItem, depth, objType):
            text = self.getText(obj)
            #print ("RECORD", depth);
            
            visible = True
            
            if objType == 'topLevelWidgets' and obj.isHidden():
                visible = False
            elif self.hasMethod(obj,'isVisible'):
                visible = obj.isVisible()

            parentItem.appendRow([
                QStandardItem( Krita.instance().icon('visible' if visible else 'novisible'), type(obj).__name__ ),
                #QStandardItem( Krita.instance().icon('novisible' if objType == 'topLevelWidgets' and obj.isHidden() else 'visible'), type(obj).__name__ ),
                QStandardItem( obj.objectName() ),
                QStandardItem( obj.metaObject().className() ),
                QStandardItem( objType ),
                QStandardItem( text )
            ])
            
            item = parentItem.child(parentItem.rowCount() - 1)
            
            item.setData( obj, 101 )
                
            return item
                
        def getText(self, obj):
            text = ''
            if self.hasMethod(obj,'text'):
                text = obj.text()
                    
            elif self.hasMethod(obj,'value'):
                text = obj.value()

            elif self.hasMethod(obj,'currentText'):
                text = obj.currentText()
                
            elif self.hasMethod(obj,'html'):
                text = obj.html()

            elif self.hasMethod(obj,'windowTitle'):
                text = obj.windowTitle()
            
            return text

        def hasMethod(self, obj, method):
            return True if hasattr(obj, method) and callable(getattr(obj, method)) else False



Krita.instance().addDockWidgetFactory(DockWidgetFactory("pluginDevToolsDocker", DockWidgetFactoryBase.DockBottom, PluginDevToolsDocker)) 
 
