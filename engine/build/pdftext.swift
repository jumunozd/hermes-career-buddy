// pdftext.swift - Extrae el texto de un PDF con PDFKit (macOS), como lo leeria una maquina.
// Lo usa build/ats_check.py cuando no hay pdftotext instalado.
// Uso: swift build/pdftext.swift archivo.pdf
import Foundation
import PDFKit

guard CommandLine.arguments.count > 1,
      let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write("no se pudo abrir el PDF\n".data(using: .utf8)!)
    exit(1)
}
print(doc.string ?? "")
