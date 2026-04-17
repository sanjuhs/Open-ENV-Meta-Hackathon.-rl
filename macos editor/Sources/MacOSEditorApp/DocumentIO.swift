import AppKit
import Foundation
import UniformTypeIdentifiers

@MainActor
struct LoadedDocument {
    let attributedText: NSAttributedString
    let kind: EditorDocumentKind
}

enum DocumentIOError: LocalizedError {
    case unsupportedFormat(String)

    var errorDescription: String? {
        switch self {
        case .unsupportedFormat(let ext):
            return "Unsupported document type: \(ext)"
        }
    }
}

@MainActor
enum DocumentIO {
    static let supportedFileTypes = ["docx", "rtf", "rtfd", "txt", "html", "htm"]
    static let supportedContentTypes = supportedFileTypes.compactMap { UTType(filenameExtension: $0) }

    static func load(from url: URL) throws -> LoadedDocument {
        let ext = url.pathExtension.lowercased()

        if ext == "txt" {
            let raw = try String(contentsOf: url, encoding: .utf8)
            return LoadedDocument(
                attributedText: DocumentStyle.gameText(raw),
                kind: .plainTextGame
            )
        }

        let options = readOptions(forExtension: ext)
        let attributed = try NSAttributedString(
            url: url,
            options: options,
            documentAttributes: nil
        )
        return LoadedDocument(attributedText: attributed, kind: .richText)
    }

    static func save(document: EditorDocument, to url: URL) throws {
        let ext = url.pathExtension.lowercased()

        if ext == "txt" {
            try document.plainString.write(to: url, atomically: true, encoding: .utf8)
            return
        }

        let fileType = try documentType(forExtension: ext)
        let attributes: [NSAttributedString.DocumentAttributeKey: Any] = [
            .documentType: fileType,
        ]
        let data = try document.attributedText.data(
            from: NSRange(location: 0, length: document.attributedText.length),
            documentAttributes: attributes
        )
        try data.write(to: url, options: .atomic)
    }

    static func suggestedFilename(for document: EditorDocument) -> String {
        if let url = document.url {
            return url.lastPathComponent
        }
        let sanitizedTitle = document.title.isEmpty ? "Untitled" : document.title
        let ext = document.kind.defaultExtension
        if sanitizedTitle.lowercased().hasSuffix(".\(ext)") {
            return sanitizedTitle
        }
        return "\(sanitizedTitle).\(ext)"
    }

    private static func readOptions(forExtension ext: String) -> [NSAttributedString.DocumentReadingOptionKey: Any] {
        guard let type = try? documentType(forExtension: ext) else {
            return [:]
        }
        return [
            .documentType: type,
        ]
    }

    private static func documentType(forExtension ext: String) throws -> NSAttributedString.DocumentType {
        switch ext {
        case "docx":
            return .officeOpenXML
        case "rtf":
            return .rtf
        case "rtfd":
            return .rtfd
        case "html", "htm":
            return .html
        case "":
            return .rtf
        default:
            throw DocumentIOError.unsupportedFormat(ext)
        }
    }
}
