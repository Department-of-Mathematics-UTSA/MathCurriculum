import pandas as pd
import numpy as np
import networkx as nx
import CurriculumGraph as CurriculumGraph
import pyodbc

class CurriculumDB:
    cnxn = None
    cursor = None
    edgesnumbers = []
    Lessons = []
    LessonsClasses = []
    CoursesDescriptions = None
    excel_file = None
    PaginaDict = {}
    PaginaDictInverse = {}
    opus_idDict = {}
    Outcomes = None
    CoursesList = []
    XrefNames = []
    XrefSheetsList = []
    Xref = None



    def __init__(self, excel_file, serverip, databasename, username, password):
        self.excel_file = excel_file
        cg = CurriculumGraph.CurriculumGraph(excel_file)
        self.Adjacency = cg.GenAdjacency(cg.Graph)
        self.cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server}; SERVER='+ serverip +'; DATABASE='+ databasename +'; UID=' + username + '; PWD=' + password)
        self.cursor = self.cnxn.cursor()
        for i in cg.SheetNameEdgesList:
            self.edgesnumbers.append(int(i.replace("Edges", "")))
        Edges = cg.GetEdges()
        Edges = Edges.to_numpy()
        for i in range(0,len(Edges[:,0])):
            self.Lessons.append(Edges[i][0])
        self.LessonsOriginal = cg.GetAliases()
        self.LessonsClasses = cg.GetAliases()
        self.CoursesList = cg.CoursesList
        self.GenLessonsClasses()
        self.GenPaginaDicts()
        self.CoursesDescriptions = pd.read_excel(cg.excel_file, sheet_name = "CourseNamesNarratives").to_numpy()
        self.Outcomes = pd.read_excel(cg.excel_file, sheet_name = "Outcomes").to_numpy()
        self.GetXrefSheetNames()
        self.GetXrefSheetsList()
        self.GenXref()

    def GenLessonsClasses(self):  # Generate the list of lessons and the classes the lessons are in 
        for i in range(0,len(self.LessonsClasses[:,0])):
            self.LessonsClasses[i][1] = int(self.LessonsClasses[i][1].replace("MAT",""))
        self.LessonsClasses[0][0] = 1
        j = 0
        for i in range(1, len(self.LessonsClasses[:,0])):
            j = j + 1
            if self.LessonsClasses[i - 1][1] == self.LessonsClasses[i][1]:
                self.LessonsClasses[i][0] = j + 1  
            else:
                self.LessonsClasses[i][0] = 1
                j = 0

    def GenPaginaDicts(self):  # Generates the dictionaries that relates the numerical lessons to the numbers within a specific class.
        for i in range(0, len(self.LessonsClasses[:,0])):
            self.PaginaDict[ self.LessonsOriginal[i][0] ] = [ self.LessonsClasses[i][0], self.LessonsClasses[i][1] ]
        for i in range(0, len(self.LessonsClasses[:,0])):
            self.PaginaDictInverse[tuple([ self.LessonsClasses[i][0], self.LessonsClasses[i][1] ])] = self.LessonsOriginal[i][0]
        for i in self.PaginaDict:
            self.opus_idDict[i] = (self.PaginaDict[i])[1]

    def GenOpus(self):  # Fills the Table OPUS that lists the classes.
        for i in self.edgesnumbers:
            self.cursor.execute("INSERT INTO OPUS (id_opus, id_artifex, id_emendator, cd_opus_type, id_created, dt_created, ds_graph) VALUES (?, 1, 1, 'LITERATRONIC', 1, GETDATE(), '')", i)
            self.cursor.execute("INSERT INTO CATEGORY(Opus, Id, Lable) VALUES (?, 1, 'Science')",i)
            self.cursor.execute("INSERT INTO CATEGORY(Opus, Id, Lable) VALUES (?, 2, 'Engineering')",i)
            self.cursor.execute("INSERT INTO CATEGORY(Opus, Id, Lable) VALUES (?, 3, 'Humanities')",i)
        self.cnxn.commit()

    def GenPagina(self): # Fills the Table PAGINA that corresponds the lessons with the list of classes and the order in the classes.
        Pagina = []
        for i in range(0,len(self.LessonsClasses[:,0])):
            Pagina.append([int(self.LessonsClasses[i][0]),int(self.LessonsClasses[i][1])])
        self.cursor.executemany("INSERT INTO PAGINA (id_pagina, id_opus, id_created, dt_created, am_link, ds_gui, pagina_type, pagina_cat) VALUES (?, ?, 1, GETDATE(), 0, NEWID(), 'PRE-REQ', 1)", Pagina)
        self.cnxn.commit()
        
    def GenLinguaOpus(self): # Fills the Table LINGUA OPUS that relates the courses to the descriptions given in the course catalog
        LinguaOpus = []
        for i in range(0,len(self.CoursesDescriptions[:,0])):
            LinguaOpus.append([self.CoursesDescriptions[i][0], "MAT" + str(self.CoursesDescriptions[i][0]) + ": " + self.CoursesDescriptions[i][1], self.CoursesDescriptions[i][2]])
        self.cursor.executemany("SET ANSI_WARNINGS OFF; INSERT INTO LINGUA_OPUS (id_opus, cd_lingua, ds_title, ds_tag, ds_content, in_visible, id_created, dt_created) VALUES (?, 'HISPANIA', ?, ?, '', 1, 1, GETDATE())", LinguaOpus)
        self.cursor.executemany("SET ANSI_WARNINGS OFF; INSERT INTO LINGUA_OPUS (id_opus, cd_lingua, ds_title, ds_tag, ds_content, in_visible, id_created, dt_created) VALUES (?, 'BRITANNIA', ?, ?, '', 1, 1, GETDATE())", LinguaOpus)
        self.cnxn.commit()
    
    def GenLinguaPagina(self): # Fills the Table LINGUA_PAGINA that relates the lesson numbers to the descriptions given in the Wiki (as of now) 
        LinguaPagina = []
        Pagina = []
        for i in range(0,len(self.LessonsClasses[:,0])):
            Pagina.append([int(self.LessonsClasses[i][0]),int(self.LessonsClasses[i][1])])
        LastLesson = []
        for i in range(0, len(Pagina) - 1):
            if self.LessonsClasses[i][1] != self.LessonsClasses[i+1,1]:
                LastLesson.append([self.LessonsClasses[i][1], self.LessonsClasses[i][0]])
        LastLesson.append([self.LessonsClasses[-1][1], self.LessonsClasses[-1][0]])
        LastLessonCourse = None
        for i in range(0,len(Pagina)):
            for j in range(0,len(LastLesson)):
                if LastLesson[j][0] == int(self.LessonsClasses[i][1]):
                    LastLessonCourse = LastLesson[j][1]
            LinguaPagina.append([int(self.LessonsClasses[i][1]), int(self.LessonsClasses[i][0]), self.LessonsClasses[i][2], self.LessonsClasses[i][2], LastLessonCourse])
        self.cursor.executemany("INSERT INTO LINGUA_PAGINA (id_opus, id_pagina, cd_lingua, ds_title, ds_tag, ds_content, id_created, dt_created, id_capstone, ds_StartLesson) VALUES (?, ?, 'BRITANNIA', ?, ?, '', 1, GETDATE(), ?, NULL)",LinguaPagina)
        self.cnxn.commit()

    def GenMatrix(self): # Generates the MCA matrix and inserts it into the Matrix table.
        MCAFillerList = []
        for i in range(0, int(np.sqrt(self.Adjacency.size))):
            for j in range(0, int(np.sqrt(self.Adjacency.size))):
                if (self.Adjacency[i][j] > 0 and self.Adjacency[i][j] < np.infty):
                    MCAFillerList.append([self.opus_idDict[i+1], self.opus_idDict[j+1], int((self.PaginaDict[i+1])[0]), int((self.PaginaDict[j+1])[0]), int(self.Adjacency[i][j])])
        self.cursor.executemany("INSERT INTO MATRIX (cd_matrix_type, id_opus_i, id_opus, i, j, id_opus_nexus, am_value, cd_link_type, Path, Category_1, Category_2, Category_3, Category_4, Category_5, Category_6, Category_7, Category_8, Category_9, Category_10) VALUES ('MCA', ?, ?, ?, ?, NULL, ?, 'NEXT', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)",MCAFillerList)
        self.cnxn.commit()

    def GenLinguaDoctrina(self): # Fills the table Lingua_Doctrina wit the Student Learning Outcomes in the Doctrina tables to a description of them.
        Doctrina = []
        for i in range(0, len(self.Outcomes[:,0])):
            Doctrina.append([self.Outcomes[i][0], 'BRITANNIA', self.Outcomes[i][1]])
        self.cursor.executemany("INSERT INTO LINGUA_DOCTRINA (id_doctrina, cd_lingua, ds_doctrina, dt_created, dt_edited,  id_created, id_edited) VALUES (?,?,?,GETDATE(),GETDATE(), 1, 1)",Doctrina)
        self.cnxn.commit()

    def GetXrefSheetNames(self): # Generates the list of sheet names
        for i in range(len(self.CoursesList)):
            if self.CoursesList[i].startswith("XREF"):
                self.XrefNames.append(self.CoursesList[i])

    def GetXrefSheetsList(self): # Generates the list of sheets of edges as elements
        for i in range(len(self.XrefNames)):
            self.XrefSheetsList.append(pd.read_excel(self.excel_file, sheet_name = self.XrefNames[i]))

    def GenXref(self): # Generates the .csv file of edges from a .xslx
        pd.concat(self.XrefSheetsList).to_csv("xref.csv", index=False, header=False)
        self.Xref = pd.read_csv(r'xref.csv', header=None).to_numpy()

    def GenDoctrina(self): # Fills the Table DOCTRINA of SLOs.
        XrefByOpus = []
        for i in range(0,len(self.Xref[:,0])):
            XrefByOpus.append([int((self.PaginaDict[self.Xref[i][0]])[0]), int((self.PaginaDict[self.Xref[i][0]])[1]), int(self.Xref[i][1])])
        self.cursor.executemany("INSERT INTO DOCTRINA (id_pagina, id_opus, id_doctrina, dt_created, dt_edited, id_created, id_edited) VALUES (?, ?, ?, GETDATE(), GETDATE(), 1, 1)",XrefByOpus)
        self.cursor.commit()