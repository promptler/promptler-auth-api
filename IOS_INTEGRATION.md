# iOS Integration Guide

This guide shows how to integrate the Promptler Auth API with your iOS app for Apple Sign-In.

## Overview

The integration involves:
1. Implementing Apple Sign-In in your iOS app
2. Collecting device information
3. Sending authentication data to the API
4. Handling responses and errors

## Prerequisites

- Xcode 14+
- iOS 13+ (for Sign in with Apple)
- Apple Developer account with Sign in with Apple capability enabled

## Step 1: Configure App for Apple Sign-In

### 1.1 Enable Sign in with Apple Capability

In Xcode:
1. Select your project
2. Select your target
3. Go to "Signing & Capabilities"
4. Click "+ Capability"
5. Add "Sign in with Apple"

### 1.2 Update Info.plist

No special configuration needed for Sign in with Apple.

## Step 2: Create API Client

Create a Swift file for the Auth API client:

```swift
import Foundation
import AuthenticationServices

// MARK: - API Models

struct DeviceProfile: Codable {
    let model: String?
    let name: String?
    let systemName: String?
    let systemVersion: String?
    let locale: String?
    let region: String?
    let timeZone: String?
    let appVersion: String?
    let appBuild: String?

    enum CodingKeys: String, CodingKey {
        case model, name
        case systemName = "system_name"
        case systemVersion = "system_version"
        case locale, region
        case timeZone = "time_zone"
        case appVersion = "app_version"
        case appBuild = "app_build"
    }
}

struct AppleSignInRequest: Codable {
    let appleUserId: String
    let displayName: String?
    let email: String?
    let deviceProfile: DeviceProfile?
    let identityToken: String?
    let timestamp: Date

    enum CodingKeys: String, CodingKey {
        case appleUserId = "apple_user_id"
        case displayName = "display_name"
        case email
        case deviceProfile = "device_profile"
        case identityToken = "identity_token"
        case timestamp
    }
}

struct AppleSignInResponse: Codable {
    let appleUserId: String
    let displayName: String?
    let email: String?
    let latestDeviceProfile: [String: Any]?
    let firstSeenAt: Date
    let lastUpdatedAt: Date
    let created: Bool

    enum CodingKeys: String, CodingKey {
        case appleUserId = "apple_user_id"
        case displayName = "display_name"
        case email
        case latestDeviceProfile = "latest_device_profile"
        case firstSeenAt = "first_seen_at"
        case lastUpdatedAt = "last_updated_at"
        case created
    }
}

// MARK: - API Client

class PromptlerAuthAPI {
    static let shared = PromptlerAuthAPI()

    // IMPORTANT: Store these securely in Keychain in production!
    private let baseURL = "https://auth.yourdomain.com"
    private let apiKey = "YOUR_API_KEY_HERE" // Store in Keychain!

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        // Configure date formatting
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: - Device Info Collection

    private func collectDeviceProfile() -> DeviceProfile {
        let device = UIDevice.current

        // Get app version and build
        let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String
        let appBuild = Bundle.main.infoDictionary?["CFBundleVersion"] as? String

        // Get locale and region
        let locale = Locale.current.identifier
        let region = Locale.current.regionCode

        // Get timezone
        let timeZone = TimeZone.current.identifier

        return DeviceProfile(
            model: device.modelName, // See extension below
            name: device.name,
            systemName: device.systemName,
            systemVersion: device.systemVersion,
            locale: locale,
            region: region,
            timeZone: timeZone,
            appVersion: appVersion,
            appBuild: appBuild
        )
    }

    // MARK: - API Methods

    func signIn(
        appleUserId: String,
        displayName: String?,
        email: String?,
        identityToken: String?
    ) async throws -> AppleSignInResponse {
        let url = URL(string: "\(baseURL)/v1/auth/apple")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let requestData = AppleSignInRequest(
            appleUserId: appleUserId,
            displayName: displayName,
            email: email,
            deviceProfile: collectDeviceProfile(),
            identityToken: identityToken,
            timestamp: Date()
        )

        request.httpBody = try encoder.encode(requestData)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthAPIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw AuthAPIError.httpError(statusCode: httpResponse.statusCode)
        }

        return try decoder.decode(AppleSignInResponse.self, from: data)
    }

    func updateDeviceMetadata(appleUserId: String) async throws {
        let url = URL(string: "\(baseURL)/v1/auth/apple/\(appleUserId)")!

        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let requestData: [String: Any] = [
            "device_profile": try encoder.encode(collectDeviceProfile()),
            "timestamp": ISO8601DateFormatter().string(from: Date())
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: requestData)

        let (_, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthAPIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw AuthAPIError.httpError(statusCode: httpResponse.statusCode)
        }
    }
}

// MARK: - Errors

enum AuthAPIError: Error {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)
    case networkError(Error)

    var localizedDescription: String {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

// MARK: - UIDevice Extension

extension UIDevice {
    var modelName: String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let machineMirror = Mirror(reflecting: systemInfo.machine)
        let identifier = machineMirror.children.reduce("") { identifier, element in
            guard let value = element.value as? Int8, value != 0 else { return identifier }
            return identifier + String(UnicodeScalar(UInt8(value)))
        }

        // Map identifier to human-readable name
        switch identifier {
        case "iPhone14,2": return "iPhone 13 Pro"
        case "iPhone14,3": return "iPhone 13 Pro Max"
        case "iPhone14,4": return "iPhone 13 mini"
        case "iPhone14,5": return "iPhone 13"
        case "iPhone14,7": return "iPhone 14"
        case "iPhone14,8": return "iPhone 14 Plus"
        case "iPhone15,2": return "iPhone 14 Pro"
        case "iPhone15,3": return "iPhone 14 Pro Max"
        case "iPhone15,4": return "iPhone 15"
        case "iPhone15,5": return "iPhone 15 Plus"
        case "iPhone16,1": return "iPhone 15 Pro"
        case "iPhone16,2": return "iPhone 15 Pro Max"
        default: return identifier
        }
    }
}
```

## Step 3: Implement Apple Sign-In

Create a view controller or SwiftUI view for Sign in with Apple:

### SwiftUI Example

```swift
import SwiftUI
import AuthenticationServices

struct SignInWithAppleButton: View {
    @State private var isSignedIn = false
    @State private var errorMessage: String?
    @State private var isLoading = false

    var body: some View {
        VStack(spacing: 20) {
            if isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle())
            } else {
                SignInWithAppleButton(.signIn) { request in
                    request.requestedScopes = [.fullName, .email]
                }
                onCompletion: { result in
                    handleSignInResult(result)
                }
                .frame(height: 50)
                .cornerRadius(8)
            }

            if let error = errorMessage {
                Text(error)
                    .foregroundColor(.red)
                    .font(.caption)
            }
        }
        .padding()
    }

    private func handleSignInResult(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            if let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential {
                handleAppleIDCredential(appleIDCredential)
            }

        case .failure(let error):
            errorMessage = "Sign in failed: \(error.localizedDescription)"
        }
    }

    private func handleAppleIDCredential(_ credential: ASAuthorizationAppleIDCredential) {
        isLoading = true
        errorMessage = nil

        // Extract user ID
        let appleUserId = credential.user

        // Extract name (only on first sign-in)
        var displayName: String?
        if let fullName = credential.fullName {
            let components = [fullName.givenName, fullName.familyName]
                .compactMap { $0 }
            displayName = components.joined(separator: " ")
        }

        // Extract email (only on first sign-in)
        let email = credential.email

        // Extract identity token
        var identityToken: String?
        if let tokenData = credential.identityToken,
           let token = String(data: tokenData, encoding: .utf8) {
            identityToken = token
        }

        // Send to backend
        Task {
            do {
                let response = try await PromptlerAuthAPI.shared.signIn(
                    appleUserId: appleUserId,
                    displayName: displayName,
                    email: email,
                    identityToken: identityToken
                )

                // Save user ID to UserDefaults or Keychain
                UserDefaults.standard.set(appleUserId, forKey: "appleUserId")

                // Handle successful sign-in
                await MainActor.run {
                    isSignedIn = true
                    isLoading = false
                }

                print("Sign in successful: \(response)")

            } catch {
                await MainActor.run {
                    errorMessage = "Authentication failed: \(error.localizedDescription)"
                    isLoading = false
                }
            }
        }
    }
}
```

### UIKit Example

```swift
import UIKit
import AuthenticationServices

class SignInViewController: UIViewController {

    override func viewDidLoad() {
        super.viewDidLoad()
        setupSignInButton()
    }

    private func setupSignInButton() {
        let button = ASAuthorizationAppleIDButton(type: .signIn, style: .black)
        button.addTarget(self, action: #selector(handleSignInTapped), for: .touchUpInside)

        view.addSubview(button)
        button.translatesAutoresizingMaskIntoConstraints = false

        NSLayoutConstraint.activate([
            button.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            button.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            button.widthAnchor.constraint(equalToConstant: 280),
            button.heightAnchor.constraint(equalToConstant: 50)
        ])
    }

    @objc private func handleSignInTapped() {
        let provider = ASAuthorizationAppleIDProvider()
        let request = provider.createRequest()
        request.requestedScopes = [.fullName, .email]

        let controller = ASAuthorizationController(authorizationRequests: [request])
        controller.delegate = self
        controller.presentationContextProvider = self
        controller.performRequests()
    }
}

extension SignInViewController: ASAuthorizationControllerDelegate {
    func authorizationController(controller: ASAuthorizationController,
                                didCompleteWithAuthorization authorization: ASAuthorization) {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
            return
        }

        let appleUserId = credential.user

        var displayName: String?
        if let fullName = credential.fullName {
            let components = [fullName.givenName, fullName.familyName].compactMap { $0 }
            displayName = components.joined(separator: " ")
        }

        let email = credential.email

        var identityToken: String?
        if let tokenData = credential.identityToken,
           let token = String(data: tokenData, encoding: .utf8) {
            identityToken = token
        }

        Task {
            do {
                let response = try await PromptlerAuthAPI.shared.signIn(
                    appleUserId: appleUserId,
                    displayName: displayName,
                    email: email,
                    identityToken: identityToken
                )

                UserDefaults.standard.set(appleUserId, forKey: "appleUserId")

                print("Sign in successful: \(response)")

                // Navigate to main app
                await MainActor.run {
                    // Your navigation code here
                }

            } catch {
                print("Authentication failed: \(error)")
                // Show error to user
            }
        }
    }

    func authorizationController(controller: ASAuthorizationController,
                                didCompleteWithError error: Error) {
        print("Sign in failed: \(error.localizedDescription)")
        // Show error to user
    }
}

extension SignInViewController: ASAuthorizationControllerPresentationContextProviding {
    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        return view.window!
    }
}
```

## Step 4: Handle App Launch

Check for existing credentials on app launch:

```swift
import AuthenticationServices

class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

        // Check Apple Sign-In status
        checkAppleSignInStatus()

        return true
    }

    private func checkAppleSignInStatus() {
        guard let appleUserId = UserDefaults.standard.string(forKey: "appleUserId") else {
            // User not signed in
            return
        }

        let provider = ASAuthorizationAppleIDProvider()
        provider.getCredentialState(forUserID: appleUserId) { state, error in
            switch state {
            case .authorized:
                // User is still authorized, optionally update device metadata
                Task {
                    try? await PromptlerAuthAPI.shared.updateDeviceMetadata(appleUserId: appleUserId)
                }

            case .revoked, .notFound:
                // Sign out user
                UserDefaults.standard.removeObject(forKey: "appleUserId")
                // Show sign-in screen

            default:
                break
            }
        }
    }
}
```

## Step 5: Secure API Key Storage

**IMPORTANT:** Never hardcode API keys in your app. Use Keychain:

```swift
import Security

class KeychainHelper {
    static func save(key: String, value: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]

        SecItemDelete(query as CFDictionary)
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    static func get(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let value = String(data: data, encoding: .utf8) else {
            return nil
        }

        return value
    }
}

// Usage:
// Store API key on first launch or during onboarding
KeychainHelper.save(key: "api_key", value: "your-api-key-here")

// Retrieve when needed
if let apiKey = KeychainHelper.get(key: "api_key") {
    // Use apiKey
}
```

## Step 6: Error Handling

Implement proper error handling for common scenarios:

```swift
enum SignInError: LocalizedError {
    case userCancelled
    case invalidCredentials
    case networkError
    case serverError(Int)
    case unknown

    var errorDescription: String? {
        switch self {
        case .userCancelled:
            return "Sign in was cancelled"
        case .invalidCredentials:
            return "Invalid credentials received from Apple"
        case .networkError:
            return "Network connection failed"
        case .serverError(let code):
            return "Server error: \(code)"
        case .unknown:
            return "An unknown error occurred"
        }
    }
}
```

## Testing

### Test with Sandbox Environment

1. Use a test Apple ID in Settings > App Store > Sandbox Account
2. Test the sign-in flow
3. Verify data is sent to your API
4. Check database for user record

### Test Checklist

- [ ] First-time sign-in creates user record
- [ ] Subsequent sign-ins update existing record
- [ ] Device profile is collected correctly
- [ ] Identity token is sent and verified
- [ ] Error handling works properly
- [ ] API key is stored securely in Keychain
- [ ] Credential state check works on app launch
- [ ] Sign out clears stored data

## Best Practices

1. **Always send identity token** in production for security
2. **Store API keys in Keychain**, never in code or UserDefaults
3. **Handle all error cases** gracefully with user-friendly messages
4. **Check credential state** on app launch
5. **Update device metadata** periodically (e.g., on app launch)
6. **Implement retry logic** for network errors
7. **Log errors** for debugging (but don't log sensitive data)

## Troubleshooting

### "Invalid Client" Error
- Verify bundle ID matches in Apple Developer Portal and API configuration
- Check that Sign in with Apple capability is enabled

### "Invalid Token" Error
- Ensure identity token is being sent
- Check that APPLE_BUNDLE_ID in API matches your app
- Verify token hasn't expired (should be used immediately)

### Network Errors
- Check that base URL is correct
- Verify SSL certificate is valid
- Ensure device has internet connection

## Support

For API-related issues, check the API logs:
```bash
sudo journalctl -u promptler-auth -f
```

For iOS integration help, consult Apple's documentation:
- [Sign in with Apple Documentation](https://developer.apple.com/sign-in-with-apple/)
- [ASAuthorizationAppleIDProvider](https://developer.apple.com/documentation/authenticationservices/asauthorizationappleidprovider)

---

**Last Updated:** January 2024
