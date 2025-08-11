# TapSnap iOS (SwiftUI) – Starter Files

These Swift files are drop-in starters. Create an iOS App project in Xcode
(Swift + SwiftUI), then add these files to your project.

Later, replace `AdyenPaymentService` stub with the real Adyen Tap to Pay SDK integration.

## Suggested steps

1. Open Xcode → Create a new project → iOS **App** → Product Name: `TapSnap`.
2. Interface: **SwiftUI**, Language: **Swift**. Save the project.
3. Drag the files from `ios/` into your Xcode project (copy if needed).
4. Run on device or simulator (payment screen uses a Mock service in Simulator).
5. When Adyen access is ready, add the Adyen SDK via SPM and implement `AdyenPaymentService`.
