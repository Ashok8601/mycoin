import os
import argparse
from uuid import uuid4
from api.node_api import app, blockchain, node_identifier # node_api से Flask app और blockchain ऑब्जेक्ट को इंपोर्ट करें

# ----------------------------------------------------
# 1. कॉन्फ़िगरेशन और तर्क (Configuration & Arguments)
# ----------------------------------------------------

def run_node():
    """
    कमांड लाइन आर्गुमेंट्स के आधार पर नोड को चलाता है।
    """
    # आर्गुमेंट पार्सर सेट करें
    parser = argparse.ArgumentParser(description="MyCoin Blockchain Node")
    parser.add_argument(
        '-p', '--port', 
        type=int, 
        default=5000, 
        help='The port to run the node on (e.g., 5000, 5001)'
    )
    
    # शुरुआती नोड्स को रजिस्टर करने के लिए आर्गुमेंट (वैकल्पिक)
    parser.add_argument(
        '--connect', 
        type=str, 
        nargs='*', # 0 या अधिक नोड एड्रेस स्वीकार करता है
        help='A list of initial peer node URLs to connect to (e.g., http://localhost:5001)'
    )

    args = parser.parse_args()
    port = args.port
    
    print("--------------------------------------------------")
    print("       🚀 MyCoin Blockchain Node Initializing      ")
    print("--------------------------------------------------")
    print(f"Node ID: {node_identifier}")
    print(f"Initial Difficulty: {blockchain.difficulty}")
    print(f"Genesis Block Index: {blockchain.last_block['index']}")
    
    # 2. शुरुआती नोड्स को रजिस्टर करें
    if args.connect:
        print("\nConnecting to peer nodes...")
        for peer in args.connect:
            if peer.strip() and not peer.endswith(f":{port}"): # खुद से कनेक्ट न करें
                blockchain.register_node(peer.strip())
                print(f"  -> Registered: {peer.strip()}")
        
        # कनेक्ट होने के बाद सर्वसम्मति से चेन सिंक करें
        print("\nAttempting Consensus...")
        replaced = blockchain.resolve_conflicts()
        if replaced:
            print("Chain successfully synchronized with the network.")
            blockchain.balance_manager.recalculate_balances() # चेन बदलने के बाद बैलेंस अपडेट करें
        else:
            print("Local chain is authoritative.")


    # 3. Flask App चलाएँ
    print(f"\nStarting API server on port: {port}...")
    
    # डिबग मोड को पब्लिक लॉन्च के लिए False पर रखें
    app.run(host='0.0.0.0', port=port, debug=False) 

if __name__ == '__main__':
    run_node()