import Foundation

protocol PaymentService {
    func startTapToPay(amountCents: Int) async throws -> String // returns Adyen pspReference
}

// Simulator/dev mock (always 'authorises')
final class MockPaymentService: PaymentService {
    func startTapToPay(amountCents: Int) async throws -> String {
        try await Task.sleep(nanoseconds: 1_000_000_000)
        return "PSP_TEST_\(Int.random(in: 100000...999999))"
    }
}

// Placeholder for real Adyen integration
final class AdyenPaymentService: PaymentService {
    func startTapToPay(amountCents: Int) async throws -> String {
        // TODO: integrate Adyen Tap to Pay SDK flow here
        // Return pspReference when authorisation succeeds
        return "PSP_REF_PLACEHOLDER"
    }
}
