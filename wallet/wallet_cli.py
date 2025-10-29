import json
import requests
import os
import argparse

# core/cryptos.py से आवश्यक फ़ंक्शन इंपोर्ट करें
from core.cryptos import generate_wallet, sign_transaction 

# ----------------------------------------------------
# ग्लोबल सेटिंग्स
# ----------------------------------------------------
# वॉलेट फ़ाइलों को यहीं सेव किया जाएगा
WALLET_DIR = 'wallet_data'
# जिस नोड से यह वॉलेट बात करेगा (हमारा API)
NODE_URL = 'http://localhost:5000' 

# ----------------------------------------------------
# 1. वॉलेट फ़ाइल प्रबंधन
# ----------------------------------------------------

def load_wallet(filename='my_key.json'):
    """ वॉलेट फ़ाइल से प्राइवेट की और एड्रेस लोड करें """
    path = os.path.join(WALLET_DIR, filename)
    if not os.path.exists(path):
        return None
    # 🌟 FIX: यहाँ load_wallet फ़ंक्शन का अधूरा लॉजिक पूरा किया गया है 🌟
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ त्रुटि: वॉलेट फ़ाइल '{filename}' को पढ़ने में विफल रहा। ({e})")
        return None

def save_wallet(wallet_data, filename='my_key.json'):
    """ वॉलेट डेटा को JSON फ़ाइल में सेव करें """
    if not os.path.exists(WALLET_DIR):
        os.makedirs(WALLET_DIR)
    path = os.path.join(WALLET_DIR, filename)
    with open(path, 'w') as f:
        json.dump(wallet_data, f, indent=4)
    print(f"\n🔑 वॉलेट सफलतापूर्वक सेव किया गया: {path}")


# ----------------------------------------------------
# 2. वॉलेट फंक्शन्स
# ----------------------------------------------------

def create_new_wallet():
    """ एक नया वॉलेट बनाता है और उसे सेव करता है """
    wallet = generate_wallet()
    
    print("\n--- नया MyCoin वॉलेट ---")
    print("WARNING: अपनी प्राइवेट की को कभी किसी को न दें!")
    print(f"Address: {wallet['public_address']}")
    
    # फ़ाइल नाम पूछें
    filename = input("\nसेव करने के लिए फ़ाइल नाम (जैसे: 'alice_key.json'): ")
    if not filename.endswith('.json'):
        filename += '.json'
        
    save_wallet(wallet, filename)
    return wallet

def get_balance_cli(address):
    """ नोड API से बैलेंस प्राप्त करें """
    try:
        response = requests.get(f'{NODE_URL}/balance/{address}')
        response.raise_for_status() 
        
        balance = response.json().get('balance', 0.0)
        print(f"\n💰 एड्रेस {address[:10]}... पर बैलेंस: {balance} MyCoin")
        return balance
    except requests.exceptions.ConnectionError:
        print(f"\n❌ नोड कनेक्शन त्रुटि: सुनिश्चित करें कि आपका नोड ({NODE_URL}) चल रहा है।")
    except Exception as e:
        print(f"\n❌ त्रुटि: {e}")

def create_and_send_transaction(wallet_data):
    """ ट्रांजैक्शन बनाता है, साइन करता है और नोड को भेजता है """
    sender = wallet_data['public_address']
    
    print("\n--- नया ट्रांजैक्शन ---")
    recipient = input("प्राप्तकर्ता का पता (Recipient Address): ")
    try:
        amount = float(input("भेजी जाने वाली राशि (Amount): "))
    except ValueError:
        print("❌ अमान्य राशि।")
        return

    # 1. ट्रांजैक्शन साइन करें
    signature = sign_transaction(
        wallet_data['private_key'], 
        sender, 
        recipient, 
        amount
    )
    
    if not signature:
        print("❌ हस्ताक्षर बनाने में त्रुटि।")
        return

    # 2. ट्रांजैक्शन डेटा तैयार करें
    transaction_data = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'signature': signature
    }

    # 3. नोड API को भेजें
    try:
        response = requests.post(f'{NODE_URL}/transactions/new', json=transaction_data)
        response.raise_for_status() 
        
        print("\n✅ ट्रांजैक्शन सफलतापूर्वक भेजा गया!")
        print(f"नोड प्रतिक्रिया: {response.json()['message']}")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ नोड कनेक्शन त्रुटि: सुनिश्चित करें कि आपका नोड ({NODE_URL}) चल रहा है।")
    except requests.exceptions.HTTPError as e:
        # 406 Not Acceptable (हस्ताक्षर त्रुटि या अपर्याप्त फंड) को यहाँ हैंडल किया जाता है
        print(f"\n❌ ट्रांजैक्शन त्रुटि: {e.response.json().get('message', 'Unknown error')}")
    except Exception as e:
        print(f"\n❌ एक अनपेक्षित त्रुटि हुई: {e}")

def display_public_address_cli(address):
    """ पब्लिक एड्रेस को स्पष्ट रूप से डिस्प्ले करें (वेब UI के लिए कॉपी करने हेतु) """
    print("\n---------------------------------------------------------")
    print("📋 आपकी पब्लिक की (वेब UI में पेस्ट करने के लिए):")
    print(f"\n{address}")
    print("\n---------------------------------------------------------")


# ----------------------------------------------------
# 3. मुख्य CLI मेनू
# ----------------------------------------------------

def main_menu():
    """ वॉलेट CLI मेनू """
    while True:
        print("\n\n=== MyCoin Wallet CLI ===")
        print("1. 🔑 नया वॉलेट बनाएँ और सेव करें")
        print("2. 💾 मौजूदा वॉलेट लोड करें")
        print("3. ❌ बाहर निकलें")
        
        choice = input("विकल्प चुनें: ")
        
        if choice == '1':
            create_new_wallet()
        elif choice == '2':
            filename = input("लोड करने के लिए फ़ाइल नाम (जैसे: 'alice_key.json'): ")
            loaded_wallet = load_wallet(filename)
            if loaded_wallet:
                wallet_actions_menu(loaded_wallet)
            else:
                print("❌ फ़ाइल नहीं मिली।")
        elif choice == '3':
            break
        else:
            print("अमान्य विकल्प।")

def wallet_actions_menu(wallet_data):
    """ लोड किए गए वॉलेट के साथ कार्य करें """
    address = wallet_data['public_address']
    
    while True:
        print(f"\n--- वॉलेट एड्रेस: {address[:10]}... ---")
        print("1. 💰 बैलेंस देखें")
        print("2. ✍️ कॉइन भेजें (नया ट्रांजैक्शन)")
        print("3. 📋 Public Key डिस्प्ले करें (वेब UI के लिए)")
        print("4. ⬅️ मेन मेनू पर वापस जाएँ")
        
        choice = input("विकल्प चुनें: ")
        
        if choice == '1':
            get_balance_cli(address)
        elif choice == '2':
            create_and_send_transaction(wallet_data)
        elif choice == '3':
            display_public_address_cli(address)
        elif choice == '4':
            break
        else:
            print("अमान्य विकल्प।")

if __name__ == '__main__':
    # कमांड लाइन आर्गुमेंट पार्सर सेट करें ताकि NODE_URL को बदला जा सके
    parser = argparse.ArgumentParser(description="MyCoin Wallet CLI")
    parser.add_argument(
        '-n', '--node', 
        type=str, 
        default='http://localhost:5000', 
        help='The URL of the MyCoin node API (default: http://localhost:5000)'
    )
    args = parser.parse_args()
    NODE_URL = args.node
    
    print(f"Connecting to node at: {NODE_URL}")
    main_menu()
