import Foundation

final class APIClient {
    static let shared = APIClient()
    private init() {}

    // Set to your backend URL
    var baseURL = URL(string: "http://127.0.0.1:8000")!

    func createTransaction(merchantId: Int, amountCents: Int, currency: String = "USD") async throws -> Transaction {
        let url = baseURL.appendingPathComponent("/api/v1/transactions/")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = NewTransactionRequest(merchant_id: merchantId, amount_cents: amountCents, currency: currency)
        req.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: req)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(Transaction.self, from: data)
    }

    func confirmTransaction(id: Int, pspReference: String) async throws -> Transaction {
        let url = baseURL.appendingPathComponent("/api/v1/transactions/\(id)/confirm?psp_reference=\(pspReference)&status=authorised")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        let (data, _) = try await URLSession.shared.data(for: req)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(Transaction.self, from: data)
    }
}
