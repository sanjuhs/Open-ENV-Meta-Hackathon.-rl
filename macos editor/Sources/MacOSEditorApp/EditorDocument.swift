import AppKit
import Foundation

enum EditorDocumentKind: String {
    case richText
    case plainTextGame

    var defaultExtension: String {
        switch self {
        case .richText:
            return "docx"
        case .plainTextGame:
            return "txt"
        }
    }

    var displayName: String {
        switch self {
        case .richText:
            return "Rich Document"
        case .plainTextGame:
            return "Game Text"
        }
    }
}

@MainActor
final class EditorDocument: ObservableObject, Identifiable {
    let id = UUID()

    @Published var title: String
    @Published var attributedText: NSAttributedString
    @Published var url: URL?
    @Published var kind: EditorDocumentKind
    @Published var isDirty: Bool
    @Published var linkedGameSessionID: String?

    private(set) var revision: Int = 0

    init(
        title: String,
        attributedText: NSAttributedString,
        url: URL? = nil,
        kind: EditorDocumentKind,
        isDirty: Bool = false,
        linkedGameSessionID: String? = nil
    ) {
        self.title = title
        self.attributedText = attributedText
        self.url = url
        self.kind = kind
        self.isDirty = isDirty
        self.linkedGameSessionID = linkedGameSessionID
    }

    var plainString: String {
        attributedText.string
    }

    var displayTitle: String {
        if isDirty {
            return "● \(title)"
        }
        return title
    }

    var filePathDescription: String {
        url?.path ?? "Unsaved"
    }

    func replaceContents(_ newValue: NSAttributedString, markDirty: Bool) {
        attributedText = newValue
        isDirty = markDirty
        revision += 1
    }

    func updateFromEditor(_ newValue: NSAttributedString) {
        attributedText = newValue
        isDirty = true
        revision += 1
    }

    func markSaved(to url: URL) {
        self.url = url
        self.title = url.lastPathComponent
        self.isDirty = false
        revision += 1
    }

    static func blankRichText(title: String = "Untitled.docx") -> EditorDocument {
        EditorDocument(
            title: title,
            attributedText: DocumentStyle.defaultRichText(""),
            kind: .richText
        )
    }

    static func plainGameDocument(title: String, text: String, linkedGameSessionID: String?) -> EditorDocument {
        EditorDocument(
            title: title,
            attributedText: DocumentStyle.gameText(text),
            kind: .plainTextGame,
            isDirty: false,
            linkedGameSessionID: linkedGameSessionID
        )
    }
}

@MainActor
enum DocumentStyle {
    static let defaultFont: NSFont = {
        NSFont(name: "Aptos", size: 14)
            ?? NSFont(name: "Calibri", size: 14)
            ?? NSFont(name: "Helvetica Neue", size: 14)
            ?? NSFont.systemFont(ofSize: 14)
    }()

    static func defaultRichText(_ text: String) -> NSAttributedString {
        NSAttributedString(
            string: text,
            attributes: [
                .font: defaultFont,
                .foregroundColor: NSColor.labelColor,
            ]
        )
    }

    static func gameText(_ text: String) -> NSAttributedString {
        NSAttributedString(
            string: text,
            attributes: [
                .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .regular),
                .foregroundColor: NSColor.labelColor,
            ]
        )
    }

    static func typingAttributes(for kind: EditorDocumentKind) -> [NSAttributedString.Key: Any] {
        switch kind {
        case .richText:
            return [
                .font: defaultFont,
                .foregroundColor: NSColor.labelColor,
            ]
        case .plainTextGame:
            return [
                .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .regular),
                .foregroundColor: NSColor.labelColor,
            ]
        }
    }
}
