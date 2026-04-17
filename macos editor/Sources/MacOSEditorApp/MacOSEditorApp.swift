import AppKit
import SwiftUI

@main
struct MacOSEditorApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup("macOS Editor") {
            RootView()
                .environmentObject(appState)
                .environmentObject(appState.gameBridge)
                .frame(minWidth: 1220, minHeight: 860)
                .alert(item: $appState.alert) { alert in
                    Alert(
                        title: Text(alert.title),
                        message: Text(alert.message),
                        dismissButton: .default(Text("OK"))
                    )
                }
        }
        .commands {
            CommandGroup(after: .newItem) {
                Button("New Document") {
                    appState.newDocument()
                }
                .keyboardShortcut("n")

                Button("Open Document...") {
                    appState.openDocuments()
                }
                .keyboardShortcut("o")

                Divider()

                Button("Save") {
                    appState.saveSelectedDocument()
                }
                .keyboardShortcut("s")

                Button("Save As...") {
                    appState.saveSelectedDocumentAs()
                }
                .keyboardShortcut("S", modifiers: [.command, .shift])
            }

            CommandMenu("Game") {
                Button("Open Game Launcher") {
                    appState.presentGameLauncher()
                }
                .keyboardShortcut("g", modifiers: [.command, .shift])

                Button("Show Game Workspace") {
                    appState.openGameWorkspace()
                }

                Button("Return to Document") {
                    appState.returnToEditor()
                }

                Divider()

                Button("Start Local Server") {
                    appState.gameBridge.startLocalServer()
                }

                Button("Check Game Health") {
                    Task { await appState.gameBridge.checkHealth() }
                }
            }

            CommandMenu("Workspace") {
                Button("Show Document Workspace") {
                    appState.returnToEditor()
                }

                Button("Show Game Workspace") {
                    appState.openGameWorkspace()
                }
            }
        }
    }
}

private struct RootView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var gameBridge: GameBridge

    var body: some View {
        VStack(spacing: 0) {
            WordTitleBar()
            RibbonTabRow()
            RibbonContent()
            DocumentStrip()
            Divider()
            workspaceContent
            StatusBar()
        }
        .background(Color(nsColor: NSColor(calibratedWhite: 0.95, alpha: 1)))
        .sheet(isPresented: $appState.isGameLauncherPresented) {
            GameLauncherSheet()
                .environmentObject(appState)
                .environmentObject(gameBridge)
                .frame(minWidth: 760, minHeight: 640)
        }
    }

    @ViewBuilder
    private var workspaceContent: some View {
        switch appState.activeWorkspace {
        case .editor:
            EditorWorkspace()
        case .game:
            GameWorkspace()
        }
    }
}

private struct WordTitleBar: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        HStack(spacing: 14) {
            RoundedRectangle(cornerRadius: 10)
                .fill(
                    LinearGradient(
                        colors: [Color(red: 0.11, green: 0.44, blue: 0.88), Color(red: 0.06, green: 0.28, blue: 0.68)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 42, height: 42)
                .overlay(
                    Image(systemName: "doc.text.fill")
                        .foregroundStyle(.white)
                        .font(.system(size: 18, weight: .semibold))
                )

            VStack(alignment: .leading, spacing: 2) {
                Text(appState.currentTitle)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white)
                Text("\(appState.activeWorkspace.title) • Lightweight Word-Style Editor")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.white.opacity(0.82))
            }

            Spacer()

            HStack(spacing: 10) {
                TitleBarButton(title: "New", action: appState.newDocument)
                TitleBarButton(title: "Open", action: appState.openDocuments)
                TitleBarButton(title: "Save", action: appState.saveSelectedDocument)
                TitleBarButton(title: "Save As", action: appState.saveSelectedDocumentAs)
                TitleBarButton(title: "Game", action: appState.presentGameLauncher, emphasis: true)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(
            LinearGradient(
                colors: [Color(red: 0.13, green: 0.42, blue: 0.82), Color(red: 0.08, green: 0.27, blue: 0.63)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
    }
}

private struct RibbonTabRow: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        HStack(spacing: 2) {
            ForEach(RibbonTab.allCases) { tab in
                Button {
                    appState.setActiveRibbonTab(tab)
                } label: {
                    Text(tab.rawValue)
                        .font(.system(size: 13, weight: appState.activeRibbonTab == tab ? .semibold : .medium))
                        .foregroundStyle(appState.activeRibbonTab == tab ? Color.primary : Color.secondary)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(appState.activeRibbonTab == tab ? Color.white : Color.clear)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
                .buttonStyle(.plain)
            }

            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 6)
        .background(Color(nsColor: NSColor(calibratedWhite: 0.965, alpha: 1)))
    }
}

private struct RibbonContent: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var gameBridge: GameBridge

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 14) {
                switch appState.activeRibbonTab {
                case .home:
                    homeRibbon
                case .insert:
                    insertRibbon
                case .layout:
                    layoutRibbon
                case .review:
                    reviewRibbon
                case .view:
                    viewRibbon
                case .game:
                    gameRibbon
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .background(.white)
        .overlay(alignment: .bottom) {
            Divider()
        }
    }

    private var homeRibbon: some View {
        Group {
            RibbonPanel(title: "Clipboard") {
                RibbonButton(icon: "doc.badge.plus", title: "New", subtitle: "Blank") {
                    appState.newDocument()
                }
                RibbonButton(icon: "folder", title: "Open", subtitle: "Document") {
                    appState.openDocuments()
                }
                RibbonButton(icon: "square.and.arrow.down", title: "Save", subtitle: "Current") {
                    appState.saveSelectedDocument()
                }
            }

            RibbonPanel(title: "Font") {
                RibbonButton(icon: "bold", title: "Bold", subtitle: "Cmd+B") {
                    appState.toggleBold()
                }
                RibbonButton(icon: "italic", title: "Italic", subtitle: "Cmd+I") {
                    appState.toggleItalic()
                }
                RibbonButton(icon: "underline", title: "Underline", subtitle: "Style") {
                    appState.toggleUnderline()
                }
                RibbonButton(icon: "textformat.size.smaller", title: "Smaller", subtitle: "Font") {
                    appState.decreaseFontSize()
                }
                RibbonButton(icon: "textformat.size.larger", title: "Larger", subtitle: "Font") {
                    appState.increaseFontSize()
                }
            }

            RibbonPanel(title: "Paragraph") {
                RibbonButton(icon: "text.alignleft", title: "Left", subtitle: "Align") {
                    appState.setAlignment(.left)
                }
                RibbonButton(icon: "text.aligncenter", title: "Center", subtitle: "Align") {
                    appState.setAlignment(.center)
                }
                RibbonButton(icon: "text.alignright", title: "Right", subtitle: "Align") {
                    appState.setAlignment(.right)
                }
                RibbonButton(icon: "text.justify", title: "Justify", subtitle: "Align") {
                    appState.setAlignment(.justified)
                }
            }

            RibbonPanel(title: "Workspace") {
                RibbonStat(title: "Pages", value: "\(appState.pageCount)")
                RibbonStat(title: "Words", value: "\(appState.wordCount)")
                RibbonButton(icon: "play.rectangle", title: "Game", subtitle: "Launcher") {
                    appState.presentGameLauncher()
                }
            }
        }
    }

    private var insertRibbon: some View {
        Group {
            RibbonPanel(title: "Document") {
                RibbonButton(icon: "doc.badge.plus", title: "Blank", subtitle: "Page") {
                    appState.newDocument()
                }
                RibbonButton(icon: "folder", title: "Existing", subtitle: "Document") {
                    appState.openDocuments()
                }
                RibbonButton(icon: "square.and.arrow.down.on.square", title: "Save As", subtitle: "Copy") {
                    appState.saveSelectedDocumentAs()
                }
            }

            RibbonPanel(title: "Game Imports") {
                RibbonButton(icon: "square.and.arrow.down.on.square.fill", title: "Source", subtitle: "Import") {
                    appState.importGameSourceDocument()
                }
                RibbonButton(icon: "square.and.arrow.down", title: "Human", subtitle: "Import") {
                    appState.importGameHumanDocument()
                }
                RibbonButton(icon: "rectangle.on.rectangle", title: "Switch", subtitle: "To Game") {
                    appState.openGameWorkspace()
                }
            }
        }
    }

    private var layoutRibbon: some View {
        Group {
            RibbonPanel(title: "Layout") {
                RibbonStat(title: "View", value: "Print Layout")
                RibbonStat(title: "Pages", value: "\(appState.pageCount)")
                RibbonStat(title: "Canvas", value: "Paged")
            }

            RibbonPanel(title: "Document") {
                RibbonButton(icon: "doc.text", title: "Editor", subtitle: "Workspace") {
                    appState.returnToEditor()
                }
                RibbonButton(icon: "sidebar.right", title: "Game", subtitle: "Workspace") {
                    appState.openGameWorkspace()
                }
                RibbonButton(icon: "play.rectangle", title: "Launcher", subtitle: "Modal") {
                    appState.presentGameLauncher()
                }
            }
        }
    }

    private var reviewRibbon: some View {
        Group {
            RibbonPanel(title: "Review") {
                RibbonStat(title: "Spell Check", value: "Native")
                RibbonStat(title: "Word Count", value: "\(appState.wordCount)")
                RibbonStat(title: "Session", value: gameBridge.currentSession == nil ? "None" : "Active")
            }

            RibbonPanel(title: "DocEdit") {
                RibbonButton(icon: "paperplane", title: "Submit", subtitle: "Selected Doc") {
                    Task { await appState.submitSelectedDocumentToGame() }
                }
                RibbonButton(icon: "arrow.triangle.2.circlepath", title: "Sync", subtitle: "Model Draft") {
                    Task { await appState.syncSelectedDocumentToModelDraft() }
                }
                RibbonButton(icon: "play.rectangle", title: "Launcher", subtitle: "Game") {
                    appState.presentGameLauncher()
                }
            }
        }
    }

    private var viewRibbon: some View {
        Group {
            RibbonPanel(title: "Workspace") {
                RibbonButton(icon: "doc.text", title: "Document", subtitle: "Editor") {
                    appState.returnToEditor()
                }
                RibbonButton(icon: "gamecontroller", title: "Game", subtitle: "Workspace") {
                    appState.openGameWorkspace()
                }
                RibbonButton(icon: "play.rectangle", title: "Launcher", subtitle: "Modal") {
                    appState.presentGameLauncher()
                }
            }

            RibbonPanel(title: "Game Server") {
                RibbonButton(icon: "bolt.fill", title: "Start", subtitle: "Local Server") {
                    gameBridge.startLocalServer()
                }
                RibbonButton(icon: "heart.text.square", title: "Health", subtitle: "Check") {
                    Task { await gameBridge.checkHealth() }
                }
                RibbonButton(icon: "safari", title: "Browser", subtitle: "Open") {
                    gameBridge.openInBrowser()
                }
            }
        }
    }

    private var gameRibbon: some View {
        Group {
            RibbonPanel(title: "Server") {
                RibbonButton(icon: "bolt.fill", title: "Start", subtitle: "Local Server") {
                    gameBridge.startLocalServer()
                }
                RibbonButton(icon: "heart.text.square", title: "Health", subtitle: "Check") {
                    Task { await gameBridge.checkHealth() }
                }
                RibbonButton(icon: "safari", title: "Browser", subtitle: "Open") {
                    gameBridge.openInBrowser()
                }
            }

            RibbonPanel(title: "Session") {
                RibbonButton(icon: "plus.rectangle.on.rectangle", title: "New", subtitle: "Game Session") {
                    Task { await gameBridge.createNewSession() }
                }
                RibbonButton(icon: "arrow.clockwise", title: "Refresh", subtitle: "Session") {
                    Task { await gameBridge.refreshCurrentSession() }
                }
                RibbonButton(icon: "gamecontroller", title: "Open", subtitle: "Workspace") {
                    appState.openGameWorkspace()
                }
            }

            RibbonPanel(title: "Transfer") {
                RibbonButton(icon: "square.and.arrow.down", title: "Import", subtitle: "Human Doc") {
                    appState.importGameHumanDocument()
                }
                RibbonButton(icon: "paperplane", title: "Submit", subtitle: "Selected Doc") {
                    Task { await appState.submitSelectedDocumentToGame() }
                }
                RibbonButton(icon: "doc.text", title: "Return", subtitle: "To Editor") {
                    appState.returnToEditor()
                }
            }
        }
    }
}

private struct DocumentStrip: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(appState.documents) { document in
                    Button {
                        appState.selectedDocumentID = document.id
                        appState.returnToEditor()
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: document.kind == .richText ? "doc.text" : "doc.plaintext")
                                .font(.system(size: 12, weight: .medium))
                            VStack(alignment: .leading, spacing: 1) {
                                Text(document.displayTitle)
                                    .font(.system(size: 12, weight: .semibold))
                                    .lineLimit(1)
                                Text(document.kind.displayName)
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 9)
                        .background(appState.selectedDocumentID == document.id ? Color.white : Color.clear)
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(appState.selectedDocumentID == document.id ? Color.blue.opacity(0.25) : Color.gray.opacity(0.15), lineWidth: 1)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
        }
        .background(Color(nsColor: NSColor(calibratedWhite: 0.97, alpha: 1)))
    }
}

private struct EditorWorkspace: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Group {
            if let document = appState.selectedDocument {
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(document.title)
                                .font(.system(size: 18, weight: .semibold))
                            Text("\(document.kind.displayName) • \(document.filePathDescription)")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if let linkedSession = document.linkedGameSessionID {
                            Label("Linked Session \(linkedSession.prefix(8))", systemImage: "link")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.horizontal, 22)
                    .padding(.vertical, 14)
                    .background(.white)

                    RichTextEditor(document: document, appState: appState)
                }
            } else {
                ContentUnavailableView("No Document Selected", systemImage: "doc")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}

private struct GameWorkspace: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var gameBridge: GameBridge

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                Label("DocEdit Game Workspace", systemImage: "gamecontroller.fill")
                    .font(.system(size: 16, weight: .semibold))

                Spacer()

                if let session = gameBridge.currentSession {
                    Text("\(session.docType) • \(session.difficultyName)")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                }

                Button("Launcher") {
                    appState.presentGameLauncher()
                }
                .buttonStyle(.bordered)

                Button("Back To Document") {
                    appState.returnToEditor()
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 14)
            .background(.white)

            Divider()

            Group {
                if gameBridge.isServerHealthy, let url = gameBridge.browserURL {
                    VStack(spacing: 0) {
                        HStack(spacing: 10) {
                            Button("Import Source") {
                                appState.importGameSourceDocument()
                            }
                            .buttonStyle(.bordered)

                            Button("Import Human") {
                                appState.importGameHumanDocument()
                            }
                            .buttonStyle(.bordered)

                            Button("Submit Selected") {
                                Task { await appState.submitSelectedDocumentToGame() }
                            }
                            .buttonStyle(.bordered)

                            Button("Sync Draft") {
                                Task { await appState.syncSelectedDocumentToModelDraft() }
                            }
                            .buttonStyle(.bordered)

                            Spacer()

                            Text(gameBridge.statusText)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 20)
                        .padding(.vertical, 10)
                        .background(Color(nsColor: NSColor(calibratedWhite: 0.965, alpha: 1)))

                        GameWebView(url: url)
                    }
                } else {
                    VStack(spacing: 18) {
                        Image(systemName: "play.rectangle")
                            .font(.system(size: 38, weight: .regular))
                            .foregroundStyle(.blue)

                        Text("The game is separate from the editor until you activate it.")
                            .font(.system(size: 22, weight: .semibold))

                        Text("Open the Game menu at the top or use the launcher below, start the local server, and then switch into the game workspace.")
                            .font(.system(size: 14, weight: .medium))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: 560)

                        HStack(spacing: 12) {
                            Button("Open Game Launcher") {
                                appState.presentGameLauncher()
                            }
                            .buttonStyle(.borderedProminent)

                            Button("Return To Document") {
                                appState.returnToEditor()
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(nsColor: NSColor(calibratedWhite: 0.95, alpha: 1)))
                }
            }
        }
    }
}

private struct GameLauncherSheet: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var gameBridge: GameBridge

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("DocEdit Game Launcher")
                        .font(.system(size: 24, weight: .semibold))
                    Text("Start the local game, create a session, and switch the main UI into the game workspace when you are ready.")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("Close") {
                    dismiss()
                }
            }

            GroupBox {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Server")
                        .font(.system(size: 16, weight: .semibold))

                    TextField("Server URL", text: $gameBridge.serverURLString)
                        .textFieldStyle(.roundedBorder)

                    HStack(spacing: 10) {
                        Button("Start Local Server") {
                            gameBridge.startLocalServer()
                        }
                        .buttonStyle(.borderedProminent)

                        Button("Check Health") {
                            Task { await gameBridge.checkHealth() }
                        }
                        .buttonStyle(.bordered)

                        Button("Open In Browser") {
                            gameBridge.openInBrowser()
                        }
                        .buttonStyle(.bordered)
                    }

                    Text(gameBridge.statusText)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(gameBridge.isServerHealthy ? .green : .secondary)
                }
                .padding(8)
            }

            GroupBox {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Session")
                        .font(.system(size: 16, weight: .semibold))

                    HStack(spacing: 10) {
                        Button("New Game Session") {
                            Task { await gameBridge.createNewSession() }
                        }
                        .buttonStyle(.borderedProminent)

                        Button("Refresh Session") {
                            Task { await gameBridge.refreshCurrentSession() }
                        }
                        .buttonStyle(.bordered)
                    }

                    if let session = gameBridge.currentSession {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("\(session.docType) • \(session.domain) • \(session.difficultyName)")
                                .font(.system(size: 14, weight: .semibold))
                            Text(session.instruction)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                            Text("Live similarity: \(String(format: "%.4f", session.humanSimilarityLive))")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                        }

                        HStack(spacing: 10) {
                            Button("Import Source") {
                                appState.importGameSourceDocument()
                            }
                            .buttonStyle(.bordered)

                            Button("Import Human") {
                                appState.importGameHumanDocument()
                            }
                            .buttonStyle(.bordered)

                            Button("Submit Selected") {
                                Task { await appState.submitSelectedDocumentToGame() }
                            }
                            .buttonStyle(.bordered)
                        }
                    } else {
                        Text("No game session yet.")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(8)
            }

            Spacer()

            HStack {
                Text("Use the top menu bar `Game` item any time to reopen this launcher.")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Open Game Workspace") {
                    appState.openGameWorkspace()
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(nsColor: NSColor.windowBackgroundColor))
    }
}

private struct StatusBar: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var gameBridge: GameBridge

    var body: some View {
        HStack(spacing: 18) {
            Text("Print Layout")
            Text("Pages: \(appState.pageCount)")
            Text("Words: \(appState.wordCount)")
            Text("Workspace: \(appState.activeWorkspace.title)")
            Text(gameBridge.isServerHealthy ? "Game Server Ready" : "Game Server Offline")
                .foregroundStyle(gameBridge.isServerHealthy ? .green : .secondary)
            Spacer()
        }
        .font(.system(size: 11, weight: .medium))
        .padding(.horizontal, 16)
        .padding(.vertical, 7)
        .background(Color(nsColor: NSColor(calibratedWhite: 0.97, alpha: 1)))
        .overlay(alignment: .top) {
            Divider()
        }
    }
}

private struct TitleBarButton: View {
    let title: String
    let action: () -> Void
    var emphasis = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(emphasis ? Color.blue.opacity(0.9) : Color.primary)
                .padding(.horizontal, 14)
                .padding(.vertical, 9)
                .background(.white.opacity(emphasis ? 0.95 : 0.88))
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}

private struct RibbonPanel<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(spacing: 8) {
            HStack(alignment: .top, spacing: 8) {
                content
            }
            .padding(10)
            .frame(minHeight: 78, alignment: .topLeading)

            Text(title.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)
        }
        .background(Color(nsColor: NSColor(calibratedWhite: 0.985, alpha: 1)))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.gray.opacity(0.15), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

private struct RibbonButton: View {
    let icon: String
    let title: String
    let subtitle: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color(nsColor: NSColor(calibratedWhite: 0.95, alpha: 1)))
                        .frame(width: 44, height: 38)
                    Image(systemName: icon)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.primary)
                }

                VStack(spacing: 1) {
                    Text(title)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 72)
        }
        .buttonStyle(.plain)
    }
}

private struct RibbonStat: View {
    let title: String
    let value: String

    var body: some View {
        VStack(spacing: 6) {
            Text(value)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(.primary)
            Text(title)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.secondary)
        }
        .frame(width: 82, height: 66)
        .background(Color(nsColor: NSColor(calibratedWhite: 0.95, alpha: 1)))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}
