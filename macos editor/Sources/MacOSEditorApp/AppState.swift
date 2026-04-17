import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

enum WorkspaceMode: String {
    case editor
    case game

    var title: String {
        switch self {
        case .editor:
            return "Document"
        case .game:
            return "DocEdit Game"
        }
    }
}

enum RibbonTab: String, CaseIterable, Identifiable {
    case home = "Home"
    case insert = "Insert"
    case layout = "Layout"
    case review = "Review"
    case view = "View"
    case game = "Game"

    var id: String { rawValue }
}

struct AppAlert: Identifiable {
    let id = UUID()
    let title: String
    let message: String
}

@MainActor
final class AppState: ObservableObject {
    @Published var documents: [EditorDocument] = []
    @Published var selectedDocumentID: EditorDocument.ID? {
        didSet {
            refreshMetricsFromSelection()
        }
    }
    @Published var alert: AppAlert?
    @Published var activeWorkspace: WorkspaceMode = .editor
    @Published var activeRibbonTab: RibbonTab = .home
    @Published var isGameLauncherPresented = false
    @Published var pageCount = 1
    @Published var wordCount = 0

    weak var activeTextView: NSTextView?

    let repositoryRoot: URL?
    let gameBridge: GameBridge

    init() {
        let root = Self.findRepositoryRoot()
        self.repositoryRoot = root
        self.gameBridge = GameBridge(repositoryRoot: root)
        newDocument()
    }

    var selectedDocument: EditorDocument? {
        get {
            documents.first(where: { $0.id == selectedDocumentID }) ?? documents.first
        }
    }

    var currentTitle: String {
        selectedDocument?.title ?? "Untitled.docx"
    }

    func newDocument() {
        addDocument(.blankRichText())
    }

    func openDocuments() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = DocumentIO.supportedContentTypes

        guard panel.runModal() == .OK else { return }

        for url in panel.urls {
            do {
                let loaded = try DocumentIO.load(from: url)
                let document = EditorDocument(
                    title: url.lastPathComponent,
                    attributedText: loaded.attributedText,
                    url: url,
                    kind: loaded.kind
                )
                addDocument(document)
            } catch {
                showError(title: "Open Failed", message: error.localizedDescription)
            }
        }
    }

    func saveSelectedDocument() {
        guard let document = selectedDocument else { return }

        if let url = document.url {
            do {
                try DocumentIO.save(document: document, to: url)
                document.markSaved(to: url)
            } catch {
                showError(title: "Save Failed", message: error.localizedDescription)
            }
            return
        }

        saveSelectedDocumentAs()
    }

    func saveSelectedDocumentAs() {
        guard let document = selectedDocument else { return }

        let panel = NSSavePanel()
        panel.canCreateDirectories = true
        panel.isExtensionHidden = false
        panel.allowedContentTypes = DocumentIO.supportedContentTypes
        panel.nameFieldStringValue = DocumentIO.suggestedFilename(for: document)

        guard panel.runModal() == .OK, let url = panel.url else { return }

        do {
            try DocumentIO.save(document: document, to: url)
            document.markSaved(to: url)
        } catch {
            showError(title: "Save As Failed", message: error.localizedDescription)
        }
    }

    func closeSelectedDocument() {
        guard let selectedDocument else { return }
        documents.removeAll { $0.id == selectedDocument.id }
        selectedDocumentID = documents.first?.id
        if documents.isEmpty {
            newDocument()
        }
        refreshMetricsFromSelection()
    }

    func importGameSourceDocument() {
        guard let session = gameBridge.currentSession else {
            showError(title: "No Game Session", message: "Create or refresh a DocEdit game session first.")
            return
        }

        let title = "Game Source \(session.sessionID.prefix(8)).txt"
        addDocument(
            .plainGameDocument(
                title: title,
                text: session.sourceDocument,
                linkedGameSessionID: session.sessionID
            )
        )
    }

    func importGameHumanDocument() {
        guard let session = gameBridge.currentSession else {
            showError(title: "No Game Session", message: "Create or refresh a DocEdit game session first.")
            return
        }

        let title = "Game Human \(session.sessionID.prefix(8)).txt"
        addDocument(
            .plainGameDocument(
                title: title,
                text: session.humanDocument,
                linkedGameSessionID: session.sessionID
            )
        )
    }

    func submitSelectedDocumentToGame() async {
        guard let document = selectedDocument else {
            showError(title: "No Document", message: "Select a document to submit.")
            return
        }
        await gameBridge.submitHumanDocument(document.plainString)
    }

    func syncSelectedDocumentToModelDraft() async {
        guard let document = selectedDocument else {
            showError(title: "No Document", message: "Select a document to sync.")
            return
        }
        await gameBridge.syncModelDraft(document.plainString)
    }

    func presentGameLauncher() {
        isGameLauncherPresented = true
    }

    func openGameWorkspace() {
        activeWorkspace = .game
        activeRibbonTab = .game
    }

    func returnToEditor() {
        activeWorkspace = .editor
        if activeRibbonTab == .game {
            activeRibbonTab = .home
        }
    }

    func setActiveRibbonTab(_ tab: RibbonTab) {
        activeRibbonTab = tab
    }

    func setActiveTextView(_ textView: NSTextView?) {
        activeTextView = textView
    }

    func updateEditorMetrics(pageCount: Int, wordCount: Int) {
        self.pageCount = max(1, pageCount)
        self.wordCount = max(0, wordCount)
    }

    func increaseFontSize() {
        adjustFontSize(by: 1)
    }

    func decreaseFontSize() {
        adjustFontSize(by: -1)
    }

    func toggleBold() {
        toggleFontTrait(.boldFontMask)
    }

    func toggleItalic() {
        toggleFontTrait(.italicFontMask)
    }

    func toggleUnderline() {
        performOnActiveTextView { textView in
            let range = textView.selectedRange()
            let storage = textView.textStorage

            if range.length == 0 {
                let current = textView.typingAttributes[.underlineStyle] as? Int ?? 0
                let newValue = current == 0 ? NSUnderlineStyle.single.rawValue : 0
                textView.typingAttributes[.underlineStyle] = newValue
                return
            }

            storage?.beginEditing()
            storage?.enumerateAttribute(.underlineStyle, in: range, options: []) { value, subrange, _ in
                let current = value as? Int ?? 0
                let newValue = current == 0 ? NSUnderlineStyle.single.rawValue : 0
                storage?.addAttribute(.underlineStyle, value: newValue, range: subrange)
            }
            storage?.endEditing()
            textView.didChangeText()
        }
    }

    func setAlignment(_ alignment: NSTextAlignment) {
        performOnActiveTextView { textView in
            let range = textView.selectedRange()
            if range.length == 0 {
                let style = (textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle)?.mutableCopy() as? NSMutableParagraphStyle ?? NSMutableParagraphStyle()
                style.alignment = alignment
                textView.typingAttributes[.paragraphStyle] = style
                return
            }

            let storage = textView.textStorage
            storage?.beginEditing()
            storage?.enumerateAttribute(.paragraphStyle, in: range, options: []) { value, subrange, _ in
                let style = (value as? NSParagraphStyle)?.mutableCopy() as? NSMutableParagraphStyle ?? NSMutableParagraphStyle()
                style.alignment = alignment
                storage?.addAttribute(.paragraphStyle, value: style, range: subrange)
            }
            storage?.endEditing()
            textView.didChangeText()
        }
    }

    private func addDocument(_ document: EditorDocument) {
        documents.append(document)
        selectedDocumentID = document.id
        refreshMetricsFromSelection()
    }

    private func showError(title: String, message: String) {
        alert = AppAlert(title: title, message: message)
    }

    private func refreshMetricsFromSelection() {
        let words = selectedDocument?.plainString.wordCount ?? 0
        wordCount = words
        pageCount = max(pageCount, 1)
    }

    private func performOnActiveTextView(_ operation: (NSTextView) -> Void) {
        guard let textView = activeTextView else {
            NSSound.beep()
            return
        }
        operation(textView)
    }

    private func toggleFontTrait(_ trait: NSFontTraitMask) {
        performOnActiveTextView { textView in
            let range = textView.selectedRange()
            let storage = textView.textStorage

            if range.length == 0 {
                let currentFont = (textView.typingAttributes[.font] as? NSFont) ?? DocumentStyle.defaultFont
                textView.typingAttributes[.font] = Self.toggledFont(from: currentFont, trait: trait)
                return
            }

            storage?.beginEditing()
            storage?.enumerateAttribute(.font, in: range, options: []) { value, subrange, _ in
                let currentFont = (value as? NSFont) ?? DocumentStyle.defaultFont
                let toggled = Self.toggledFont(from: currentFont, trait: trait)
                storage?.addAttribute(.font, value: toggled, range: subrange)
            }
            storage?.endEditing()
            textView.didChangeText()
        }
    }

    private func adjustFontSize(by delta: CGFloat) {
        performOnActiveTextView { textView in
            let range = textView.selectedRange()
            let storage = textView.textStorage

            if range.length == 0 {
                let currentFont = (textView.typingAttributes[.font] as? NSFont) ?? DocumentStyle.defaultFont
                textView.typingAttributes[.font] = Self.resizedFont(from: currentFont, delta: delta)
                return
            }

            storage?.beginEditing()
            storage?.enumerateAttribute(.font, in: range, options: []) { value, subrange, _ in
                let currentFont = (value as? NSFont) ?? DocumentStyle.defaultFont
                let resized = Self.resizedFont(from: currentFont, delta: delta)
                storage?.addAttribute(.font, value: resized, range: subrange)
            }
            storage?.endEditing()
            textView.didChangeText()
        }
    }

    private static func toggledFont(from font: NSFont, trait: NSFontTraitMask) -> NSFont {
        let manager = NSFontManager.shared
        let hasTrait = manager.traits(of: font).contains(trait)
        if hasTrait {
            return manager.convert(font, toNotHaveTrait: trait)
        }
        return manager.convert(font, toHaveTrait: trait)
    }

    private static func resizedFont(from font: NSFont, delta: CGFloat) -> NSFont {
        let newSize = max(8, font.pointSize + delta)
        return NSFontManager.shared.convert(font, toSize: newSize)
    }

    private static func findRepositoryRoot() -> URL? {
        let fileManager = FileManager.default
        var current = URL(fileURLWithPath: fileManager.currentDirectoryPath)

        for _ in 0..<6 {
            let marker = current.appending(path: "scripts/doc-edit-game.sh")
            if fileManager.fileExists(atPath: marker.path) {
                return current
            }
            current.deleteLastPathComponent()
        }

        return nil
    }
}

private extension String {
    var wordCount: Int {
        split { $0.isWhitespace || $0.isNewline }.count
    }
}
