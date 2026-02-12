import sys
import os
import comtypes.client

wdFormatPDF = 17

in_file = "/mnt/c/Users/yyb19161/Documents/Self-Certification_Form.docx"
out_file = "/mnt/c/Users/yyb19161/Documents/Self-Certification_Form.pdf"

word = comtypes.client.CreateObject('Word.Application')
doc = word.Documents.Open(in_file)
doc.SaveAs(out_file, FileFormat=wdFormatPDF)
doc.Close()
word.Quit()