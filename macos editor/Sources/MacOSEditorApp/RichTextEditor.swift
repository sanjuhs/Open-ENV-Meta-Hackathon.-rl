import AppKit
import SwiftUI
import WebKit

private enum PageLayout {
    static let outerPadding = CGFloat(40)
    static let pageGap = CGFloat(28)
    static let pageWidth = CGFloat(820)
    static let pageHeight = CGFloat(1060)
    static let pageInsets = NSEdgeInsets(top: 88, left: 92, bottom: 88, right: 92)
    static let minimumCanvasWidth = pageWidth + outerPadding * 2

    static var textWidth: CGFloat {
        pageWidth - pageInsets.left - pageInsets.right
    }

    static var textHeightPerPage: CGFloat {
        pageHeight - pageInsets.top - pageInsets.bottom
    }
}

@MainActor
struct RichTextEditor: NSViewRepresentable {
    @ObservedObject var document: EditorDocument
    @ObservedObject var appState: AppState

    func makeCoordinator() -> Coordinator {
        Coordinator(document: document, appState: appState)
    }

    func makeNSView(context: Context) -> PagedEditorHostView {
        let hostView = PagedEditorHostView()
        context.coordinator.attach(hostView)
        context.coordinator.apply(document)
        return hostView
    }

    func updateNSView(_ hostView: PagedEditorHostView, context: Context) {
        context.coordinator.document = document
        context.coordinator.appState = appState
        context.coordinator.apply(document)
    }

    @MainActor
    final class Coordinator: NSObject, NSTextViewDelegate {
        var document: EditorDocument
        var appState: AppState

        private weak var hostView: PagedEditorHostView?
        private var appliedRevision = -1
        private var isApplyingModel = false

        init(document: EditorDocument, appState: AppState) {
            self.document = document
            self.appState = appState
        }

        func attach(_ hostView: PagedEditorHostView) {
            self.hostView = hostView
            hostView.textView.delegate = self
        }

        func apply(_ document: EditorDocument) {
            guard let hostView else { return }

            hostView.configure(for: document.kind)
            appState.setActiveTextView(hostView.textView)

            guard appliedRevision != document.revision else {
                hostView.relayoutDocument()
                publishMetrics()
                return
            }

            let selectedRange = hostView.textView.selectedRange()
            isApplyingModel = true
            hostView.textView.textStorage?.setAttributedString(document.attributedText)
            hostView.textView.typingAttributes = DocumentStyle.typingAttributes(for: document.kind)
            hostView.relayoutDocument()

            if selectedRange.location <= hostView.textView.string.count {
                hostView.textView.setSelectedRange(selectedRange)
            }

            appliedRevision = document.revision
            isApplyingModel = false
            publishMetrics()
        }

        func textDidBeginEditing(_ notification: Notification) {
            if let textView = notification.object as? NSTextView {
                appState.setActiveTextView(textView)
            }
        }

        func textViewDidChangeSelection(_ notification: Notification) {
            if let textView = notification.object as? NSTextView {
                appState.setActiveTextView(textView)
            }
        }

        func textDidChange(_ notification: Notification) {
            guard let textView = notification.object as? NSTextView, !isApplyingModel else { return }
            let current = NSAttributedString(attributedString: textView.attributedString())
            document.updateFromEditor(current)
            hostView?.relayoutDocument()
            appliedRevision = document.revision
            publishMetrics()
        }

        private func publishMetrics() {
            let pageCount = hostView?.pageCount ?? 1
            let words = document.plainString.wordCount
            appState.updateEditorMetrics(pageCount: pageCount, wordCount: words)
        }
    }
}

@MainActor
final class PagedEditorHostView: NSView {
    let scrollView = NSScrollView()
    let canvasView = PagedCanvasView()
    let textView: NSTextView

    var pageCount: Int {
        canvasView.pageCount
    }

    override init(frame frameRect: NSRect) {
        let textStorage = NSTextStorage()
        let layoutManager = NSLayoutManager()
        let textContainer = NSTextContainer(containerSize: NSSize(width: PageLayout.textWidth, height: .greatestFiniteMagnitude))
        textContainer.widthTracksTextView = false
        textContainer.heightTracksTextView = false
        layoutManager.usesFontLeading = true
        layoutManager.allowsNonContiguousLayout = true
        layoutManager.addTextContainer(textContainer)
        textStorage.addLayoutManager(layoutManager)
        textView = NSTextView(frame: .zero, textContainer: textContainer)

        super.init(frame: frameRect)
        setup()
    }

    required init?(coder: NSCoder) {
        return nil
    }

    override func layout() {
        super.layout()
        scrollView.frame = bounds
        relayoutDocument()
    }

    func configure(for kind: EditorDocumentKind) {
        textView.isRichText = kind == .richText
        textView.importsGraphics = kind == .richText
        textView.usesInspectorBar = kind == .richText
        textView.typingAttributes = DocumentStyle.typingAttributes(for: kind)
        relayoutDocument()
    }

    func relayoutDocument() {
        canvasView.relayoutDocument(viewportWidth: scrollView.contentSize.width, textView: textView)
    }

    private func setup() {
        wantsLayer = true
        layer?.backgroundColor = NSColor(calibratedWhite: 0.94, alpha: 1).cgColor

        scrollView.drawsBackground = true
        scrollView.backgroundColor = NSColor(calibratedWhite: 0.94, alpha: 1)
        scrollView.borderType = .noBorder
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.scrollerStyle = .overlay
        scrollView.automaticallyAdjustsContentInsets = false
        scrollView.contentInsets = NSEdgeInsetsZero
        scrollView.autoresizingMask = [.width, .height]

        textView.drawsBackground = false
        textView.backgroundColor = .clear
        textView.isEditable = true
        textView.isSelectable = true
        textView.isVerticallyResizable = true
        textView.isHorizontallyResizable = false
        textView.autoresizingMask = []
        textView.minSize = NSSize(width: PageLayout.textWidth, height: PageLayout.textHeightPerPage)
        textView.maxSize = NSSize(width: PageLayout.textWidth, height: .greatestFiniteMagnitude)
        textView.textContainerInset = NSSize(width: 0, height: 0)
        textView.textContainer?.lineFragmentPadding = 0
        textView.textContainer?.containerSize = NSSize(width: PageLayout.textWidth, height: .greatestFiniteMagnitude)
        textView.allowsUndo = true
        textView.isContinuousSpellCheckingEnabled = true
        textView.isGrammarCheckingEnabled = false
        textView.isAutomaticQuoteSubstitutionEnabled = false
        textView.isAutomaticDashSubstitutionEnabled = false
        textView.isAutomaticTextReplacementEnabled = true
        textView.smartInsertDeleteEnabled = true
        textView.usesFindBar = true
        textView.insertionPointColor = .labelColor

        scrollView.documentView = canvasView
        addSubview(scrollView)
    }
}

@MainActor
final class PagedCanvasView: NSView {
    override var isFlipped: Bool { true }

    private(set) var pageCount = 1

    func relayoutDocument(viewportWidth: CGFloat, textView: NSTextView) {
        let canvasWidth = max(viewportWidth, PageLayout.minimumCanvasWidth)
        let textHeight = measuredTextHeight(for: textView)
        let pages = max(1, Int(ceil(textHeight / PageLayout.textHeightPerPage)))
        let totalHeight = PageLayout.outerPadding * 2 + CGFloat(pages) * PageLayout.pageHeight + CGFloat(max(0, pages - 1)) * PageLayout.pageGap

        pageCount = pages
        frame = NSRect(x: 0, y: 0, width: canvasWidth, height: totalHeight)

        let pageOriginX = floor((canvasWidth - PageLayout.pageWidth) / 2)
        let textFrame = NSRect(
            x: pageOriginX + PageLayout.pageInsets.left,
            y: PageLayout.outerPadding + PageLayout.pageInsets.top,
            width: PageLayout.textWidth,
            height: max(textHeight, PageLayout.textHeightPerPage)
        )

        if textView.superview !== self {
            addSubview(textView)
        }

        if textView.frame != textFrame {
            textView.frame = textFrame
        }

        needsDisplay = true
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor(calibratedWhite: 0.94, alpha: 1).setFill()
        dirtyRect.fill()

        let canvasWidth = bounds.width
        let pageX = floor((canvasWidth - PageLayout.pageWidth) / 2)

        for pageIndex in 0..<pageCount {
            let y = PageLayout.outerPadding + CGFloat(pageIndex) * (PageLayout.pageHeight + PageLayout.pageGap)
            let pageRect = NSRect(x: pageX, y: y, width: PageLayout.pageWidth, height: PageLayout.pageHeight)
            drawPage(in: pageRect)
        }
    }

    private func drawPage(in rect: NSRect) {
        let shadow = NSShadow()
        shadow.shadowColor = NSColor.black.withAlphaComponent(0.08)
        shadow.shadowBlurRadius = 18
        shadow.shadowOffset = NSSize(width: 0, height: 6)

        let path = NSBezierPath(roundedRect: rect, xRadius: 6, yRadius: 6)
        NSGraphicsContext.saveGraphicsState()
        shadow.set()
        NSColor.white.setFill()
        path.fill()
        NSGraphicsContext.restoreGraphicsState()

        NSColor(calibratedWhite: 0.86, alpha: 1).setStroke()
        path.lineWidth = 1
        path.stroke()
    }

    private func measuredTextHeight(for textView: NSTextView) -> CGFloat {
        guard let layoutManager = textView.layoutManager, let textContainer = textView.textContainer else {
            return PageLayout.textHeightPerPage
        }

        layoutManager.ensureLayout(for: textContainer)
        let usedRect = layoutManager.usedRect(for: textContainer)
        return max(PageLayout.textHeightPerPage, ceil(usedRect.height) + 8)
    }
}

@MainActor
struct GameWebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.setValue(false, forKey: "drawsBackground")
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        guard webView.url != url else { return }
        webView.load(URLRequest(url: url))
    }
}

private extension String {
    var wordCount: Int {
        split { $0.isWhitespace || $0.isNewline }.count
    }
}
