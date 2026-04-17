import AppKit
import Foundation

struct GameHealthResponse: Decodable {
    let status: String
    let openenvMounted: Bool
    let defaultUI: String

    enum CodingKeys: String, CodingKey {
        case status
        case openenvMounted = "openenv_mounted"
        case defaultUI = "default_ui"
    }
}

struct GameSessionPayload: Decodable {
    let sessionID: String
    let instruction: String
    let scenarioExposition: String
    let sourceDocument: String
    let humanDocument: String
    let difficultyName: String
    let domain: String
    let docType: String
    let humanSimilarityLive: Double

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case instruction
        case scenarioExposition = "scenario_exposition"
        case sourceDocument = "source_document"
        case humanDocument = "human_document"
        case difficultyName = "difficulty_name"
        case domain
        case docType = "doc_type"
        case humanSimilarityLive = "human_similarity_live"
    }
}

struct GameSubmitHumanResponse: Decodable {
    let liveSimilarity: Double

    enum CodingKeys: String, CodingKey {
        case liveSimilarity = "live_similarity"
    }
}

private struct NewGameRequest: Encodable {
    let difficulty: Int
    let domain: String
}

private struct HumanSubmitRequest: Encodable {
    let editedDocument: String

    enum CodingKeys: String, CodingKey {
        case editedDocument = "edited_document"
    }
}

private struct ModelDraftRequest: Encodable {
    let editedDocument: String

    enum CodingKeys: String, CodingKey {
        case editedDocument = "edited_document"
    }
}

@MainActor
final class GameBridge: ObservableObject {
    @Published var serverURLString = "http://127.0.0.1:8877"
    @Published var statusText = "DocEdit server has not been checked yet."
    @Published var health: GameHealthResponse?
    @Published var currentSession: GameSessionPayload?
    @Published var isBusy = false

    let repositoryRoot: URL?

    init(repositoryRoot: URL?) {
        self.repositoryRoot = repositoryRoot
    }

    var browserURL: URL? {
        resolvedServerURL?.appending(path: "modern")
    }

    var isServerHealthy: Bool {
        health?.status == "ok"
    }

    func startLocalServer() {
        guard let repositoryRoot else {
            statusText = "Could not find the repository root, so the local DocEdit launcher could not be resolved."
            return
        }

        let scriptURL = repositoryRoot.appending(path: "scripts/doc-edit-game.sh")
        let process = Process()
        let outputPipe = Pipe()

        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = [scriptURL.path, "start", "--ui", "modern"]
        process.currentDirectoryURL = repositoryRoot
        process.standardOutput = outputPipe
        process.standardError = outputPipe

        do {
            try process.run()
            process.waitUntilExit()

            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(decoding: outputData, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)

            if process.terminationStatus == 0 {
                statusText = output.isEmpty ? "DocEdit server started." : output
            } else {
                statusText = output.isEmpty ? "DocEdit server failed to start." : output
            }
        } catch {
            statusText = "Failed to launch DocEdit server: \(error.localizedDescription)"
        }
    }

    func checkHealth() async {
        guard let url = resolvedServerURL?.appending(path: "health") else {
            statusText = "Invalid server URL."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let response: GameHealthResponse = try await load(url: url)
            health = response
            statusText = "DocEdit server is healthy. Default UI: \(response.defaultUI)."
        } catch {
            statusText = "Health check failed: \(error.localizedDescription)"
        }
    }

    func createNewSession(difficulty: Int = 2, domain: String = "any") async {
        guard let url = resolvedServerURL?.appending(path: "api/game/new") else {
            statusText = "Invalid server URL."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let payload: GameSessionPayload = try await send(
                url: url,
                method: "POST",
                body: NewGameRequest(difficulty: difficulty, domain: domain)
            )
            currentSession = payload
            statusText = "Created game session \(payload.sessionID.prefix(8)). \(payload.docType) in \(payload.domain)."
        } catch {
            statusText = "Could not create a game session: \(error.localizedDescription)"
        }
    }

    func refreshCurrentSession() async {
        guard let sessionID = currentSession?.sessionID else {
            statusText = "No current game session to refresh."
            return
        }
        guard let url = resolvedServerURL?.appending(path: "api/game/\(sessionID)") else {
            statusText = "Invalid server URL."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let payload: GameSessionPayload = try await load(url: url)
            currentSession = payload
            statusText = "Refreshed game session \(payload.sessionID.prefix(8))."
        } catch {
            statusText = "Could not refresh the current session: \(error.localizedDescription)"
        }
    }

    func submitHumanDocument(_ documentText: String) async {
        guard let sessionID = currentSession?.sessionID else {
            statusText = "Create a game session before submitting."
            return
        }
        guard let url = resolvedServerURL?.appending(path: "api/game/\(sessionID)/submit-human") else {
            statusText = "Invalid server URL."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let result: GameSubmitHumanResponse = try await send(
                url: url,
                method: "POST",
                body: HumanSubmitRequest(editedDocument: documentText)
            )
            statusText = "Submitted current document. Live similarity: \(String(format: "%.4f", result.liveSimilarity))."
            await refreshCurrentSession()
        } catch {
            statusText = "Human submit failed: \(error.localizedDescription)"
        }
    }

    func syncModelDraft(_ documentText: String) async {
        guard let sessionID = currentSession?.sessionID else {
            statusText = "Create a game session before syncing a model draft."
            return
        }
        guard let url = resolvedServerURL?.appending(path: "api/game/\(sessionID)/model-draft") else {
            statusText = "Invalid server URL."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let _: GameSessionDraftResponse = try await send(
                url: url,
                method: "POST",
                body: ModelDraftRequest(editedDocument: documentText)
            )
            statusText = "Synced the current editor text into the model workspace."
            await refreshCurrentSession()
        } catch {
            statusText = "Model draft sync failed: \(error.localizedDescription)"
        }
    }

    func openInBrowser() {
        guard let url = browserURL else {
            statusText = "Invalid server URL."
            return
        }
        NSWorkspace.shared.open(url)
    }

    private var resolvedServerURL: URL? {
        URL(string: serverURLString.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private func load<T: Decodable>(url: URL) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        let decoder = JSONDecoder()
        return try decoder.decode(T.self, from: data)
    }

    private func send<T: Decodable, Body: Encodable>(url: URL, method: String, body: Body) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        let decoder = JSONDecoder()
        return try decoder.decode(T.self, from: data)
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            return
        }
        guard (200...299).contains(http.statusCode) else {
            let body = String(decoding: data, as: UTF8.self)
            throw NSError(
                domain: "MacOSEditor.GameBridge",
                code: http.statusCode,
                userInfo: [
                    NSLocalizedDescriptionKey: body.isEmpty ? "HTTP \(http.statusCode)" : body,
                ]
            )
        }
    }
}

private struct GameSessionDraftResponse: Decodable {}
