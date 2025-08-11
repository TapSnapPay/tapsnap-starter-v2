import SwiftUI

struct HomeView: View {
    @State private var amountText: String = ""
    @State private var isProcessing = false
    @State private var showReceipt = false
    @State private var lastTransaction: Transaction?

    // Switch between MockPaymentService() and AdyenPaymentService() later
    let payment: PaymentService = MockPaymentService()
    let merchantId: Int = 1 // Replace with actual merchant id from your backend

    var amountCents: Int {
        Int((Double(amountText) ?? 0) * 100)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 18) {
                Text("TapSnap")
                    .font(.system(size: 24, weight: .semibold))
                TextField("Enter amount (e.g., 25.00)", text: $amountText)
                    .keyboardType(.decimalPad)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(12)
                Button(action: pay) {
                    if isProcessing {
                        ProgressView()
                    } else {
                        Text("Confirm & Pay")
                            .fontWeight(.semibold)
                    }
                }
                .disabled(amountCents <= 0 || isProcessing)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(14)
                .padding(.top, 4)

                Spacer()
            }
            .padding()
            .navigationDestination(isPresented: $showReceipt) {
                ReceiptView(tx: lastTransaction)
            }
        }
    }

    func pay() {
        Task {
            guard amountCents > 0 else { return }
            isProcessing = True
            do {
                // 1) Create tx on backend
                let tx = try await APIClient.shared.createTransaction(merchantId: merchantId, amountCents: amountCents)
                // 2) Start Tap to Pay (mock for now)
                let psp = try await payment.startTapToPay(amountCents: amountCents)
                // 3) Confirm with backend
                let confirmed = try await APIClient.shared.confirmTransaction(id: tx.id, pspReference: psp)
                lastTransaction = confirmed
                showReceipt = true
            } catch {
                print("Payment failed: \(error)")
            }
            isProcessing = False
        }
    }
}
