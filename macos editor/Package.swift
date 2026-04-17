// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MacOSEditor",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "MacOSEditorApp",
            targets: ["MacOSEditorApp"]
        ),
    ],
    targets: [
        .executableTarget(
            name: "MacOSEditorApp",
            path: "Sources/MacOSEditorApp"
        ),
    ]
)
