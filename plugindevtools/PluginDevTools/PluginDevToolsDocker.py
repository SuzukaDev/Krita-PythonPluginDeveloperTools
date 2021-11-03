from krita import *
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg, uic
import sip
import pprint
import time
from contextlib import redirect_stdout
import io
import re
import json


from .GetKritaAPI import *
#import asyncio
#from concurrent.futures import ProcessPoolExecutor

class PluginDevToolsDocker(DockWidget):
    def __init__(self):
        super().__init__()
        
        settingsData = Krita.instance().readSetting("", "pluginDevToolsSettings","")
        
        self.settings = {}
        if settingsData.startswith('{'):
            self.settings = json.loads(settingsData)
        
        
        
        self.kritaAPI = {}
        
        self.setWindowTitle("Plugin Developer Tools")
       
        self.centralWidget = uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + '/DockerWidget.ui')
        
        for i in range(0,self.centralWidget.tabWidget.count()):
            name = self.centralWidget.tabWidget.widget(i).objectName().replace('Tab','')
            if name not in self.settings:
                self.settings[name] = {}
        
        
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
            
            self.currentAPI = None
            
            self.kritaapiTextBrowser = self.caller.centralWidget.kritaapiTextBrowser
            self.kritaapiTreeView = self.caller.centralWidget.kritaapiTreeView
            self.kritaapiModel = QStandardItemModel()

            self.proxyModel = QSortFilterProxyModel()

            self.proxyModel.setFilterCaseSensitivity( Qt.CaseInsensitive )
            self.proxyModel.setFilterKeyColumn(-1)
            self.proxyModel.setRecursiveFilteringEnabled(True)

            self.proxyModel.setSourceModel(self.kritaapiModel)
            self.kritaapiTreeView.setModel(self.proxyModel)
            
            self.kritaTreeSelectModel = self.kritaapiTreeView.selectionModel()
            self.kritaTreeSelectModel.selectionChanged.connect(self.itemSelectionChanged)
            
            self.caller.centralWidget.kritaapiGenAutoComplete.setIcon( Krita.instance().icon('document-export') )
            self.caller.centralWidget.kritaapiDownload.setIcon( Krita.instance().icon('merge-layer-below') )
            
            self.firstRun = True
            

            
        def itemSelectionChanged(self, new, old):
            #index = self.kritaapiTreeView.currentIndex()
            #print ("selected", index)
            indexes = new.indexes()
            if indexes:
                self.kritaapiTextBrowser.setText( indexes[0].data(101) )
            
            #if index:
            #    prop = self.proxyModel.index(index.row(), 0).data(101)
            #    self.kritaapiTextBrowser.setText( prop if prop else "" )


        def selected(self):
            if self.firstRun:
                self.firstRun = False
                
                ver = (Krita.instance().version().split('-'))[0]
                
                if ver not in self.caller.settings['kritaapi']:
                    self.downloadKritaAPI()
                
                self.fillItems()
        
        def formatDoc(self, doc):
            start = doc.find('@code')
            if start > -1:
                end = doc.find('@endcode',start)
                doc = doc.replace( doc[start:end], doc[start:end].replace('<','&lt;') )
            

            doc = '<br>'.join(doc.split('\n'))
            doc = re.sub(r'\@(param|brief|return|returns) (\w+?) ',r'<b>@\1 \2</b> ', doc).replace('the</b>','</b>the').replace('a</b>','</b>a').replace('The</b>','</b>The').replace('A</b>','</b>A')
            doc = re.sub(r'\@(param) (\w+?)</b>',r'@param <u>\2</u></b>', doc)
            doc = doc.replace('@code','<div style="background-color: rgba(0,0,0,0.3); margin: 4px"><pre><code>').replace('@endcode','</code></pre></div>')
                              
            return doc
        
        def fillItems(self):
            
            ver = (Krita.instance().version().split('-'))[0]
            
            if os.path.exists( os.path.dirname(os.path.realpath(__file__)) + '.KritaAPI.'+ver+'.zip' ):
                getAPI = GetKritaAPI()

                self.caller.kritaAPI[ver] = getAPI.parseData(ver)
            
            if ver in self.caller.kritaAPI:
                self.currentAPI = self.caller.kritaAPI[ver]
            
            self.kritaapiModel.setHorizontalHeaderLabels([
                'Method', 
                'Declare/Return Type', 
                #'Description'
                ])
            rootItem = self.kritaapiModel.invisibleRootItem()
            
            
            item = QStandardItem("Krita.instance()")
            
            metaDict = self.genMethodList( 'Krita', Krita.instance(), Krita.__dict__ )
            
            rootItem.appendRow([
                item,
                QStandardItem( metaDict['declare'] if metaDict['declare'] else "\n" ),
                #QStandardItem("")
            ])
            
            
            
            kritaClassItem = rootItem.child(rootItem.rowCount() - 1)
            kritaClassItem.setData( self.formatDoc(metaDict['doc']) , 101 )
            
            for k, prop in sorted(metaDict['methods'].items()):
                kritaClassItem.appendRow([
                    QStandardItem(prop['rec'][0]),
                    QStandardItem(prop['rec'][2]),
                    #QStandardItem( self.formatDoc(prop['doc']) )
                ])
                methodItem = kritaClassItem.child(kritaClassItem.rowCount() - 1)
                methodItem.setData( self.formatDoc(prop['doc']), 101 )


            for k in dir(krita):
                if k.startswith('__') or k == 'Krita': continue
                item = QStandardItem(k)
                
                extraData = None
                
                classMeta = getattr(krita, k)
                metaDict = self.genMethodList( k, classMeta, classMeta.__dict__ )
                
                
                
                rootItem.appendRow([
                    item,
                    QStandardItem( metaDict['declare'] if metaDict['declare'] else "\n" ),
                    #QStandardItem("")
                ])
                

                
                classItem = rootItem.child(rootItem.rowCount() - 1)
                classItem.setData( self.formatDoc(metaDict['doc']), 101 )
            
                for k1, prop in sorted(metaDict['methods'].items()):
                    subitem = QStandardItem(prop['rec'][0])
                    
                    classItem.appendRow([
                        subitem,
                        QStandardItem(prop['rec'][2]),
                        #>>QStandardItem(prop['rec'][1])
                        #QStandardItem( self.formatDoc(prop['doc']) )
                    ])
                    
                    #print ("PROP", prop['name'], '' )
                    #if extraData and k in extraData and prop['name'] in extraData[k]['methods']:
                    methodItem = classItem.child(classItem.rowCount() - 1)
                    methodItem.setData( self.formatDoc(prop['doc']), 101 )
                    
                    
                if hasattr(classMeta,'staticMetaObject'):
                    parentMetaClass = classMeta.staticMetaObject.superClass()
                    
                    if parentMetaClass and not parentMetaClass.className().startswith('Q') and not parentMetaClass.className().startswith('Kis'):
                        parentMeta = getattr(krita, parentMetaClass.className())
                        
                        parentItem = QStandardItem("Inherited from " + parentMetaClass.className() )
                        classItem.appendRow([
                            parentItem,
                            QStandardItem(""),
                            #QStandardItem("")
                        ])
                        
                        
                        iclassItem = classItem.child(classItem.rowCount() - 1)
                        if self.currentAPI and parentMetaClass.className() in self.currentAPI:
                            iclassItem.setData( self.formatDoc(self.currentAPI[parentMetaClass.className()]['doc']) , 101 )

                        
                        metaDict2 = self.genMethodList( parentMetaClass.className(), parentMeta, parentMeta.__dict__ )
                        
                        
                        
                        for k2, prop2 in sorted(metaDict2['methods'].items()):
                            iclassItem.appendRow([
                                QStandardItem(prop2['rec'][0]),
                                QStandardItem(prop2['rec'][2]),
                                #QStandardItem(prop2['rec'][1])
                            ])
                            imethodItem = iclassItem.child(iclassItem.rowCount() - 1)
                            imethodItem.setData( self.formatDoc(prop2['doc']), 101 )
            
            self.caller.centralWidget.kritaapiDownload.clicked.connect(self.downloadKritaAPI)
            self.caller.centralWidget.kritaapiGenAutoComplete.clicked.connect(self.exportKritaAPI)
            self.caller.centralWidget.kritaapiFilter.textChanged.connect(self.searchTreeFilter)
            self.kritaapiTreeView.expandAll()   
    
        def exportKritaAPI(self):
            getAPI = GetKritaAPI()
            ver = (Krita.instance().version().split('-'))[0]
            content = getAPI.genAutoComplete(ver)
            
            filename, _ = QFileDialog.getSaveFileName(
                caption="Save Auto Complete file", directory='PyKrita.py', filter="Python files (*.py)"
            )
            if filename:
                f = open(filename, "w")
                f.write(content)
                f.close()

        
        def downloadKritaAPI(self):
            ver = (Krita.instance().version().split('-'))[0]
            msgbox = QMessageBox(QMessageBox.Question,'Would you like to download the API details automatically?', 
                                       '', QMessageBox.Yes | QMessageBox.No)
            msgbox.setTextFormat(Qt.RichText)
            
            msgbox.setText("""Developer Tools would like to connect to the internet to download Krita API details.
This process will only access Krita's offical git repository at invent.kde.org.
<hr>
The API is still accessable even without downloading this file, but may not be fully complete, no documentation will be available and you will not be able to generate autocomplete files.
<hr>                            
You can also do this manually by downloading the following (Unless you are on Krita Next nightly, 'master' should be replaced with the tag you plan to target, ex. 'v"""+ver+"""' or 'v"""+ver+"""-beta1'):<br>
<u>https://invent.kde.org/graphics/krita/-/archive/master/krita-master.zip?path=libs/libkis</u>
<br>
And place it in:<br>
<u>""" + os.path.dirname(os.path.realpath(__file__)) + """.KritaAPI."""+ver+""".zip</u>
<hr>
This only needs to be done once per new version of Krita. Do note that Krita may freeze up for about a minute.
<hr>
Would you like to download the API details(less than 200kb of data) automatically?
""")

            if msgbox.exec() == QMessageBox.Yes:
                getAPI = GetKritaAPI()
                res = getAPI.updateData(ver)
                
                if res['status'] == 0:
                    msgbox = QMessageBox(QMessageBox.Warning,'Error',str(res['error']))
           
                    msgbox.exec()
                    print ( "ERROR!", str(e) )
                    return
                else:
                    QMessageBox(QMessageBox.Information,'Success!', "API details have been downloaded successfully!").exec()
                
                self.caller.kritaAPI[ver] = getAPI.parseData(ver)
                
                self.caller.settings['kritaapi'][ver] = { 'updated':res['data']['updated'] }
            
                Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
                
                #print ("CCC", self.caller.kritaAPI[ver] )
                self.kritaapiModel.clear()
                self.fillItems()
            else:
                self.caller.settings['kritaapi'][ver] = { 'updated':'0000-00-00T00:00:00' }
            
                Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
    
    
        
        
        def unselected(self):
            pass

        def searchTreeFilter(self, text):
            self.proxyModel.setFilterFixedString(text)
            self.kritaapiTreeView.expandAll()
            
            indexes = self.kritaapiTreeView.selectionModel().selectedIndexes()
                       
            if indexes:
                self.kritaapiTreeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)



        def genMethodList(self, className, obj, meta ):
            declareMethod = obj.__doc__ + "\n" if obj.__doc__ else ""
            metaDict = { 'properties':{}, 'methods':{}, 'doc':"\n\n@declare Methods\n\n@code" + declareMethod + "@endcode", 'declare': declareMethod }
            metaDict2 = { 'properties':{}, 'methods':{}, 'declare':[] }
            
            proxyObj = {}
           
            if self.currentAPI and className in self.currentAPI:
                #print ("META3!", className)
                metaDict2 = self.genMethodList3(className, self.currentAPI[ className ] )
                metaDict['doc'] = self.currentAPI[ className ]['doc'] + "\n\n@declare Methods\n\n@code" + declareMethod + "@endcode\n"
            
                for key in metaDict2['methods']:
                    if key not in meta.keys() and key != className:
                        #print ("proxy",metaDict2['methods'][key]['rec'])
                        proxyObj[key] = {
                            '__doc__': metaDict2['methods'][key]['rec'][0] + " -> " + metaDict2['methods'][key]['rec'][2],
                            }

                for decl in metaDict2['declare']:
                    metaDict['declare'] += decl['rec'][0] + " -> " + decl['rec'][2] + "\n"
                    metaDict['doc'] += "\n" + decl['doc'] + "\n@code" + decl['rec'][0] + " -> " + decl['rec'][2] + "@endcode\n"
            
            elif hasattr(obj,'staticMetaObject'):
                metaDict2 = self.genMethodList2(obj, obj.staticMetaObject)
                
                for key in metaDict2['methods']:
                    if key not in meta.keys() and key != className:
                        #print ("proxy",metaDict2['methods'][key]['rec'])
                        proxyObj[key] = {
                            '__doc__': metaDict2['methods'][key]['rec'][0] + " -> " + metaDict2['methods'][key]['rec'][2],
                            }
             
            for key in list(meta.keys()) + list(proxyObj.keys()):
                if not key.startswith('__'):
                    doc = proxyObj[key]['__doc__'] if key in proxyObj else getattr(obj,key).__doc__
                    
                    if doc:
                        staticMethod = False

                        propName = doc.split(' -> ')
                        if '(self' not in propName[0] and key not in proxyObj:
                            staticMethod = True
                        else:
                            propName[0] = propName[0].replace('(self, ','(').replace('(self','(')
                        
                        propName2 = ''
                        
                        propName[0] = re.sub(r"(Union\[.+?\])", lambda s: ' | '.join(s.group(1).split(', ')), propName[0] )
                        propName[0] = re.sub(r"(Dict\[.+?\])", lambda s: ' ; '.join(s.group(1).split(', ')), propName[0] )
                        propDoc = ''
                        
                        if key in metaDict2['methods']:
                            #print ("FOUND", key, metaDict2['methods'][key]['doc'])
                            propDoc = metaDict2['methods'][key]['doc']
                            propName2 = metaDict2['methods'][key]['rec'][0]

                            if key in proxyObj:
                                propName[0] = propName2 + ' {*}'
                                propDoc += "\n\n{*} Method is not located in " + className + ".sip. This means the method is either private, internal use only or a developer forgot to add it"
                            else:
                                propName[0] = re.sub(
                                    r"\((.+)\)", 
                                    lambda s: "(" + ', '.join( [  metaDict2['methods'][key]['pnames'][i] + ': ' + v  for i, v in enumerate(s.group(1).split(', ')) ]  ) + ")", 
                                    propName[0]
                                )
                            if 'Private' in metaDict2['methods'][key]['rec'][1]:
                                propName[0] = propName[0] + " [private]"
                            #del metaDict2['methods'][key] #testing
                            
                        if staticMethod:
                            propName[0] = propName[0] + " [static]"

                        metaDict['methods'][propName[0]]={ 'class': className, 'type':8, 'doc':propDoc, 'name': key, 'rec':[ propName[0], '', (propName[1] if len(propName) == 2 else 'void')  ] }
                
            
            for t in metaDict2['methods']:
                metaDict2['methods'][t]={}
            #print ("EXTRA", className, metaDict2  )
            return metaDict

        def genMethodList3(self, className, meta):
            metaDict = { 'properties':{}, 'methods':{}, 'classes':{}, 'declare':[] }
        
            for key in meta['methods']:
                #print ("key", key)
                #print ("m", meta['methods'][key])
                metaDict['methods'][key]={ 
                    'doc': meta['methods'][key]['doc'], 
                    'class': className, 
                    'type':0, 
                    'name': key, 
                    'pnames': [ p['name'] for p in meta['methods'][key]['params'] ], 
                    'rec':[ key+'('+', '.join([ p['type']+' '+p['name']+('='+p['optional'] if p['optional'] else '') for p in meta['methods'][key]['params'] ])+')', meta['methods'][key]['access'], meta['methods'][key]['return'] ] }

            for declare in meta['declare']:
                #print ("m", declare)
                metaDict['declare'].append({ 
                    'doc': declare['doc'], 
                    'class': className, 
                    'type':0, 
                    'name': className, 
                    'pnames': [ p['name'] for p in declare['params'] ], 
                    'rec':[ className+'('+', '.join([ p['type']+' '+p['name']+('='+p['optional'] if p['optional'] else '') for p in declare['params'] ])+')', declare['access'], className ] })

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
                        if len(pnames) > len(metaDict['methods'][methShortName]['pnames']):
                            metaDict['methods'][methShortName]['pnames'] = [ str(name, 'utf-8') for name in pnames]
                    else:    
                        metaDict['methods'][methShortName]={ 'doc':'', 'class': className, 'type':0, 'name': methShortName, 'pnames': [ str(name, 'utf-8') for name in pnames], 'rec':[ methName, methType, meth.typeName() ] }
                    #>>metaDict['methods'][methName]={ 'class': className, 'type':0, 'name': str(meth.name(), 'utf-8'), 'rec':[ methName, methType, meth.typeName() ] }

            return metaDict

    class PluginDevToolsConsole():
        EXECUTE_KEYS = [
            ['Enter', Qt.Key_Return, Qt.NoModifier ],
            ['Shift + Enter', Qt.Key_Return, Qt.ShiftModifier ],
            ['Ctrl + E', Qt.Key_E, Qt.ControlModifier ],
            ['Ctrl + F5', Qt.Key_F5, Qt.ControlModifier ],
        ]
        
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.tempFilePath = os.path.dirname(os.path.realpath(__file__)) + ".console.temp.py"
            self.watcher = None
            self.currentExecuteKey = self.EXECUTE_KEYS[0]
            
            self.historyTreeView = self.caller.centralWidget.consoleOutputBrowser
            self.historyModel = QStandardItemModel()

            self.proxyModel = QSortFilterProxyModel()

            self.proxyModel.setSourceModel(self.historyModel)
            self.historyTreeView.setModel(self.proxyModel)
            
            self.textEdit = self.caller.centralWidget.consoleInputTextEdit
            
            self.caller.centralWidget.consoleClearBtn.setIcon( Krita.instance().icon('list-remove') )
            #self.caller.centralWidget.consoleDefaultExecuteBtn.setIcon( Krita.instance().icon('config-keyboard') )
            
            self.caller.centralWidget.consoleTempScriptFileBtn.setIcon( Krita.instance().icon('edit-rename') )
            self.caller.centralWidget.consoleSetScriptFileBtn.setIcon( Krita.instance().icon('document-open') )
            
            self.caller.centralWidget.boolConsoleBindSTDOUT.setVisible(False)
            
            self.textEditFilter = self.textEditFilterClass(self)
            self.textEdit.installEventFilter(self.textEditFilter)
            
            self.caller.centralWidget.consoleClearBtn.clicked.connect(self.clearConsole)
            
            self.caller.centralWidget.consoleTempScriptFileBtn.toggled.connect(self.tempScriptFile)
            self.caller.centralWidget.consoleSetScriptFileBtn.toggled.connect(self.setScriptFile)
            
            for key in self.EXECUTE_KEYS:
                self.caller.centralWidget.consoleDefaultExecuteCmb.addItem( key[0], key[1] )
                
            self.caller.centralWidget.consoleDefaultExecuteCmb.currentIndexChanged.connect(self.executeKeyChanged)

            self.caller.centralWidget.consoleDefaultExecuteCmb.setCurrentIndex( 
                caller.settings['console']['execute_key'] if 'execute_key' in caller.settings['console'] else 0
            )
            
            self.caller.centralWidget.consoleAutoExecuteModeCmb.currentIndexChanged.connect(self.slotAutoExecuteModeChanged)

            self.caller.centralWidget.consoleAutoExecuteModeCmb.setCurrentIndex( 
                caller.settings['console']['auto_execute_mode'] if 'auto_execute_mode' in caller.settings['console'] else 0
            )
            
            self.caller.centralWidget.consoleFilter.textChanged.connect(self.searchTreeFilter)
            
            if 'watch_file' in caller.settings['console']:
                if caller.settings['console']['watch_file'] == self.tempFilePath:
                    self.caller.centralWidget.consoleTempScriptFileBtn.setChecked(True)
                else:
                    self.caller.centralWidget.consoleSetScriptFileBtn.setChecked(True)
            
            self.firstRun = True

        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                
   
        
        def unselected(self):
            pass
        
        def executeKeyChanged(self, i):
            self.currentExecuteKey = self.EXECUTE_KEYS[i]
            self.caller.settings['console']['execute_key']=i
            Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
        
        def clearConsole(self):
            self.historyModel.clear()
            
        def tempScriptFile(self, toggle):
            tbtn = self.caller.centralWidget.consoleTempScriptFileBtn
            sbtn = self.caller.centralWidget.consoleSetScriptFileBtn
            
            if toggle:
                if sbtn.isChecked():
                    self.setScriptFile(False)
                
                tempFile = QUrl.fromLocalFile( self.tempFilePath )
            
                if not os.path.exists( tempFile.toLocalFile() ):
                    f = open(tempFile.toLocalFile(),'w+')
                    f.write("# Script Name: Temp File Script\n\n")
                    f.close()
            
                QDesktopServices.openUrl( tempFile )
                if self.watchFile(tempFile.toLocalFile()):
                    tbtn.setChecked(True)
            else:
                self.unwatchFile()
                tbtn.setChecked(False)


        def setScriptFile(self, toggle):
            tbtn = self.caller.centralWidget.consoleTempScriptFileBtn
            sbtn = self.caller.centralWidget.consoleSetScriptFileBtn
            
            
            if toggle:
                if tbtn.isChecked():
                    self.tempScriptFile(False)
                
                filename, _ = QFileDialog.getOpenFileName(
                    caption="Open script python file...", filter="Python files (*.py)"
                )
                if filename:

                    QDesktopServices.openUrl( QUrl.fromLocalFile(filename) )
                    if self.watchFile(filename):
                        sbtn.setChecked(True)
            else:
                self.unwatchFile()
                sbtn.setChecked(False)
        
        def unwatchFile(self, inputFile = None):
            if self.watcher:
                if inputFile is None:
                    inputFile = self.caller.settings['console']['watch_file']
                    del self.caller.settings['console']['watch_file']
                    Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
                    
                self.watcher.fileChanged.disconnect(self.slotFileChanged)
                self.watcher.removePath(inputFile)
                self.watcher = None
            
        
        def watchFile(self, inputFile):
            if self.watcher is None:
                self.watcher = QFileSystemWatcher()
                self.watcher.fileChanged.connect(self.slotFileChanged)
                
            if self.watcher.addPath(inputFile):
                self.caller.settings['console']['watch_file']=inputFile
                Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
                return True
            else:        
                return False
        
        
        def slotFileChanged(self):
            f = open(self.caller.settings['console']['watch_file'], "r")
            fdata = f.read()
            
            if 'auto_execute_mode' not in self.caller.settings['console'] or self.caller.settings['console']['auto_execute_mode'] == 0:
                self.executeCode(fdata)
            else:
                self.textEdit.setPlainText(fdata)
            
        
        def slotAutoExecuteModeChanged(self, i):
            self.caller.settings['console']['auto_execute_mode'] = i
            Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
        
        def executeCode(self, script = None):
            if not script:
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


        def searchTreeFilter(self, text):
            self.proxyModel.setFilterRole(Qt.DisplayRole)
            self.proxyModel.setFilterFixedString(text)

        class textEditFilterClass(QWidget):
            def __init__(self, caller, parent=None):
                super().__init__()
                self.caller = caller
            
            def eventFilter(self, obj, event):
                etype = event.type()
                if etype == 6 and event.key() == self.caller.currentExecuteKey[1] and QApplication.keyboardModifiers() == self.caller.currentExecuteKey[2]:
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
        KEY_MODS = [
            [Qt.ShiftModifier, Qt.Key_Shift],
            [Qt.ControlModifier, Qt.Key_Control],
            [Qt.AltModifier, Qt.Key_Alt],
            [Qt.MetaModifier, Qt.Key_Meta],
            ]
        def __init__(self, caller):
            super().__init__()
            self.caller = caller
            
            self.modKey = self.KEY_MODS[0]
            
            self.windowFilter = self.windowFilterClass(self)
            
            self.selectorOutput = caller.centralWidget.selectorOutputLabel
            caller.centralWidget.selectorKeyCmb.currentIndexChanged.connect(self.changeSelectorModifier)
            
            caller.centralWidget.selectorKeyCmb.setCurrentIndex( 
                caller.settings['selector']['modkey'] if 'modkey' in caller.settings['selector'] else 0
            )
            
            
            self.currentWidget = None
            self.currentWindow = None
            
            
            
            self.useStyleSheet = "*[DevToolsHoverWithSelector='true'] { background-color: rgba(0, 0, 155, 50); border: 1px solid #000080; }"
            self.useStyleSheet = None
            
            #self.caller.qwin.setStyleSheet( self.caller.qwin.styleSheet() + '*[DevToolsHoverWithSelector="true"] { background-color: rgba(0, 0, 155, 50); border: 1px solid #000080; }' )
            self.createSelector(self.caller.qwin)
            
        def changeSelectorModifier(self, i):
            self.caller.settings['selector']['modkey'] = i
            Krita.instance().writeSetting("", "pluginDevToolsSettings", json.dumps(self.caller.settings) )
            self.modKey = self.KEY_MODS[i]
            
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
                    if self.selectorWidget and not sip.isdeleted(self.selectorWidget):
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
                    self.caller.t['inspector'].firstRun = True
                    self.caller.t['inspector'].refreshItems(self.currentWidget)
                    #self.caller.t['inspector'].selectItemByRef(self.currentWidget)
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
            if obj and not sip.isdeleted(obj) and obj is not self.currentWidget and self.findAncestor(self.currentWindow,obj):
                self.selectorWidget.setVisible(True)

                if self.useStyleSheet:
                    if self.currentWidget:
                        self.currentWidget.setProperty('DevToolsHoverWithSelector', False)
                        self.currentWidget.setStyleSheet(self.currentWidget.styleSheet().replace(self.useStyleSheet,""))
                    obj.setProperty('DevToolsHoverWithSelector', True)
                    obj.setStyleSheet(obj.styleSheet() + self.useStyleSheet)
                    obj.update()
                
                
                
                if hasattr(obj, 'geometry'):
                    rect = obj.geometry()
                    if obj.metaObject().superClass().className() == 'QLayout' or obj.metaObject().superClass().className() == 'QBoxLayout':
                        layoutItem = obj.itemAt(0)
                        if layoutItem is None or layoutItem.widget() is None:
                            return
                        pos = layoutItem.widget().mapTo(self.currentWindow, QPoint(0,0) )
                    else:
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
                
                if etype == 129 or (etype == 6 and event.key() == self.caller.modKey[1]):
                    if etype == 6 and event.key() == self.caller.modKey[1]:
                        win = QtWidgets.qApp.activeWindow()
                        self.caller.selectorWidget=win.findChild(QWidget, "DevToolsSelectorWidget", Qt.FindDirectChildrenOnly)
                    
                    if QApplication.keyboardModifiers() == self.caller.modKey[0]:
                        pos = QCursor.pos()
                        onWidget = QApplication.widgetAt(pos)
                        self.caller.setCurrentSelector(onWidget)
                elif etype == 7 and event.key() == self.caller.modKey[1] and self.caller.currentWidget:
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
            self.currentTableItem = None
            
            self.treeObjList = []
            
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
            
            self.showCurrentWidgetHighlight = False
            
            self.caller.centralWidget.inspectorSelectorBtn.toggled.connect(self.showCurrentWidget)
            #self.caller.centralWidget.inspectorSelectorBtn.released.connect(self.hideCurrentWidget)
            
            self.caller.centralWidget.inspectorUpdateLayoutWidget.setVisible(False)
            self.tableView.doubleClicked.connect(self.showUpdateLayout)
            
            self.caller.centralWidget.inspectorUpdateBtn.pressed.connect(self.commitUpdateLayout)
            self.caller.centralWidget.inspectorUpdateCancelBtn.pressed.connect(self.hideUpdateLayout)
                    
            self.caller.centralWidget.inspectorFilter.textChanged.connect(self.searchTreeFilter)
            self.firstRun = False

        def selected(self):
            if not self.firstRun:
                self.firstRun = True
                for win in QApplication.instance().topLevelWidgets():
                    if isinstance(win, QMainWindow):
                        self.loadTreeItems(win, 0, 'topLevelWidgets')
            if self.showCurrentWidgetHighlight:
                self.showCurrentWidget(True)
        
        def unselected(self):
            if self.showCurrentWidgetHighlight:
                self.showCurrentWidget(False, True)
        
        def showUpdateLayout(self, rec):
            if sip.isdeleted(self.currentWidget): return
            self.currentTableItem = rec
            prop = self.proxyTableModel.index( rec.row(), 0 ).data()
            print ("DC", rec.column(), rec.row(), prop, "set"+prop[0].capitalize() + prop[1:], hasattr( self.currentWidget, "set"+prop[0].capitalize() + prop[1:] ) )
            if rec.column() == 2:
                if hasattr( self.currentWidget, "set"+prop[0].capitalize() + prop[1:] ):
                    self.caller.centralWidget.inspectorUpdateTextEdit.setPlainText( str(self.currentWidget.property(prop)) )
                    self.caller.centralWidget.inspectorUpdateLayoutWidget.setVisible(True)

        def hideUpdateLayout(self):
            self.caller.centralWidget.inspectorUpdateLayoutWidget.setVisible(False)

        def commitUpdateLayout(self):

            rec = self.currentTableItem
            prop = str(self.proxyTableModel.index( rec.row(), 0 ).data())
            
            attrName = "set" + prop[0].capitalize() + prop[1:]
            
            attrValue = self.caller.centralWidget.inspectorUpdateTextEdit.toPlainText()
            
            attrType = type(self.currentWidget.property(prop)).__name__
            

            
            if attrType == 'bool':
                attrValue = True if attrValue.capitalize() == 'True' or attrValue == '1' or attrValue == 't' else False
            elif attrType == 'int':
                attrValue = int(attrValue)
            elif attrType == 'float':
                attrValue = float(attrValue)
            elif attrType == 'QRect':
                params = tuple( map(int, (attrValue.split('QRect('))[1].replace(")","").split(",") ) )
                attrValue = QRect(*params)
            elif attrType == 'QRectF':
                params = tuple( map(float, (attrValue.split('QRectF('))[1].replace(")","").split(",") ) )
                attrValue = QRect(*params)
            elif attrType == 'QPoint':
                params = tuple( map(int, (attrValue.split('QPoint('))[1].replace(")","").split(",") ) )
                attrValue = QPoint(*params)
            elif attrType == 'QPointF':
                params = tuple( map(float, (attrValue.split('QPointF('))[1].replace(")","").split(",") ) )
                attrValue = QPointF(*params)
            elif attrType == 'QSize':
                params = tuple( map(int, (attrValue.split('QSize('))[1].replace(")","").split(",") ) )
                attrValue = QPoint(*params)
            elif attrType == 'QSizeF':
                params = tuple( map(float, (attrValue.split('QSizeF('))[1].replace(")","").split(",") ) )
                attrValue = QPointF(*params)


            if hasattr(self.currentWidget,attrName):
                getattr(self.currentWidget,attrName)( attrValue )
                self.proxyTableModel.setData(self.proxyTableModel.index( rec.row(), 2 ), pprint.pformat(attrValue) )
            else:
                attrName = "to" + prop[0].capitalize() + prop[1:]
                if hasattr(self.currentWidget,attrName):
                    getattr(self.currentWidget,attrName)( attrValue )
                    self.proxyTableModel.setData(self.proxyTableModel.index( rec.row(), 2 ), pprint.pformat(attrValue) )

        
        def showCurrentWidget(self, toggle, switchTab = False):
            if toggle:
                self.showCurrentWidgetHighlight = True
                self.caller.t['selector'].currentWindow = win = QtWidgets.qApp.activeWindow()
                self.caller.t['selector'].selectorWidget=win.findChild(QWidget, "DevToolsSelectorWidget", Qt.FindDirectChildrenOnly)
                self.caller.t['selector'].setCurrentSelector(self.currentWidget, False)
            else:
                if switchTab is False:
                    self.showCurrentWidgetHighlight = False
                self.caller.t['selector'].stopSampling(False)
            
        
        def refreshItems(self, currentItem = None):
            self.treeObjList = []
            self.caller.centralWidget.inspectorFilter.setText("")
            self.treeModel.clear()
            self.treeModel.setHorizontalHeaderLabels(['Class', 'Name', 'Meta Class', 'From', 'Text/Value'])
            
            for win in QApplication.instance().topLevelWidgets():
                if isinstance(win, QMainWindow):
                    self.loadTreeItems(win, 0, 'topLevelWidgets', None, currentItem)
            if self.currentWidget:
                self.loadItemInfo( self.currentWidget )
                indexes = self.treeView.selectionModel().selectedIndexes()
                       
                if indexes:
                    self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)

                
        
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
            self.proxyTreeModel.setFilterRole(Qt.DisplayRole)
            if len(text) >= 3:
                self.proxyTreeModel.setFilterFixedString(text)
                self.treeView.expandAll()
            else:
                self.treeView.collapseAll()
                self.proxyTreeModel.setFilterFixedString("")
                
            #self.proxyTreeModel.setFilterWildcard("*{}*".format(text))
            
            indexes = self.treeView.selectionModel().selectedIndexes()
                       
            if indexes:
                self.treeView.expand(indexes[0])
                self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)
                self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)

        
        def selectItemByRef(self, obj):
            pass
            #self.proxyTreeModel.setFilterRole(102)
            #self.proxyTreeModel.setFilterFixedString( str(id(obj)) )
            #self.proxyTreeModel.setFilterFixedString( "" )
            #indexes = self.proxyTreeModel.match( self.proxyTreeModel.index(0,0) , 102, hex(id(obj)), 1, Qt.MatchRecursive )
            #print ("MATCH", indexes)
            #if indexes:
            #    #self.treeSelectModel.select( indexes[0], self.treeSelectModel.Select | self.treeSelectModel.Rows )
            #    self.treeView.expand(indexes[0])
            #    self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)
            #    self.treeView.scrollTo(indexes[0], QAbstractItemView.PositionAtCenter)
            #idx = self.treeModel.match( self.treeModel.index(0,0) , 101, obj, 1, Qt.MatchRecursive )
            #if idx:
            #    print ( idx[0].row() )
            
                #>>self.treeSelectModel.select(idx[0], self.treeSelectModel.Select | self.treeSelectModel.Rows )
        
        def itemSelectionChanged(self, new, old):
            indexes = new.indexes()
            if indexes:
                obj = self.treeObjList[indexes[0].data(101)]
                if sip.isdeleted(obj):
                    item = self.treeModel.itemFromIndex( self.proxyTreeModel.mapToSource(indexes[0]) )
                    item.setIcon( Krita.instance().icon('window-close') )
                else:
                    self.loadItemInfo( obj )
        
        def loadItemInfo(self, obj):
            self.hideUpdateLayout()
            if sip.isdeleted(obj): return
        
            self.currentWidget = obj
            
            if self.showCurrentWidgetHighlight:
                self.caller.t['selector'].setCurrentSelector(self.currentWidget, False)
        
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
            
        def loadTreeItems(self, pObj, depth, objType, parentItem = None, currentItem = None):
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
            
            
            if currentItem and pObj is currentItem:
                idx = parentItem.index()
                self.treeSelectModel.select( self.proxyTreeModel.mapFromSource(idx) , self.treeSelectModel.Select | self.treeSelectModel.Rows )
                self.treeView.expand(idx)
                #print ("TREE", idx, parentItem.text() )
                
                onItem = parentItem
                for i in range(0,depth-1):
                    onItem = onItem.parent()
                    idx = onItem.index()
                    self.treeView.expand( self.proxyTreeModel.mapFromSource(idx) )
                    #print ("TREE=", i, idx.row(), onItem.text() )
                
                
                
                
            
            for cObj in pObj.children():
                cObjType = objType
                if type(cObj).__name__ == 'QWidget' and cObj.objectName() == 'qt_scrollarea_viewport' and self.hasMethod(pObj,'viewport'):
                    cObjType = "viewport/children"
                
                item = self.setItem(cObj, parentItem, depth, cObjType)
                
                #if self.hasMethod(cObj,'viewport'):
                #    self.loadTreeItems(cObj.viewport(), depth + 1, 'viewport', item)
                    
                if self.hasMethod(cObj,'children') and type(cObj).__name__ != 'PluginDevToolsDocker':
                    #print ("CH", cObj.children())
                    
                    self.loadTreeItems(cObj, depth + 1, 'children', item, currentItem)
                    
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
            
            
            item.setData( len(self.treeObjList), 101 )
            self.treeObjList.append(obj)
                
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
