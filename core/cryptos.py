from Crypto.PublicKey import ECC
from Crypto.Hash import SHA256
from Crypto.Signature import DSS
import json
import base64

# ----------------------------------------------------
# 1. वॉलेट/की जनरेशन (Wallet/Key Generation)
# ----------------------------------------------------

def generate_wallet():
    """
    एक प्राइवेट और पब्लिक की जोड़ी (Key Pair) बनाता है।
    प्राइवेट की (Private Key) - केवल आपके पास रहती है, ट्रांजैक्शन साइन करने के लिए।
    पब्लिक की (Public Key) - आपका पता (Address), जिसे आप दुनिया को देते हैं।
    """
    # NIST P-256 कर्व का उपयोग करें, जो एक मजबूत एन्क्रिप्शन स्टैंडर्ड है
    key = ECC.generate(curve='P-256')
    
    # प्राइवेट की को PEM फॉर्मेट में एन्कोड करें (सुरक्षित स्टोर करने के लिए)
    private_key_pem = key.export_key(format='PEM')
    
    # पब्लिक की को DER फॉर्मेट में एन्कोड करें
    public_key_der = key.public_key().export_key(format='DER')
    
    # पब्लिक की को बेस64 में एन्कोड करके एक पढ़ने लायक स्ट्रिंग एड्रेस बनाएँ
    address = base64.b64encode(public_key_der).decode('utf-8')
    
    return {
        'private_key': private_key_pem.decode('utf-8'),
        'public_address': address
    }

# ----------------------------------------------------
# 2. ट्रांजैक्शन हैशिंग और सिग्नेचर
# ----------------------------------------------------

def hash_transaction(sender, recipient, amount):
    """
    ट्रांजैक्शन डेटा का एक कंसिस्टेंट हैश बनाता है
    """
    transaction_data = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
    }
    # सॉर्टेड JSON स्ट्रिंग का उपयोग करें ताकि हमेशा एक जैसा हैश बने
    encoded_transaction = json.dumps(transaction_data, sort_keys=True).encode()
    return SHA256.new(encoded_transaction)

def sign_transaction(private_key_pem, sender, recipient, amount):
    """
    प्राइवेट की का उपयोग करके ट्रांजैक्शन पर डिजिटल हस्ताक्षर (Sign) करता है।
    """
    try:
        # PEM फॉर्मेट से प्राइवेट की को इंपोर्ट करें
        key = ECC.import_key(private_key_pem)
        
        # ट्रांजैक्शन का हैश बनाएँ
        h = hash_transaction(sender, recipient, amount)
        
        # हस्ताक्षर बनाएँ
        signer = DSS.new(key, 'fips-186-3')
        signature_bytes = signer.sign(h)
        
        # हस्ताक्षर को बेस64 में एन्कोड करके स्ट्रिंग के रूप में रिटर्न करें
        return base64.b64encode(signature_bytes).decode('utf-8')
        
    except Exception as e:
        # हस्ताक्षर विफल होने पर None रिटर्न करें
        print(f"Signing Error: {e}")
        return None

def verify_signature(public_address, signature_b64, sender, recipient, amount):
    """
    जाँच करता है कि ट्रांजैक्शन पर दिया गया हस्ताक्षर वैध (Valid) है या नहीं।
    """
    try:
        # पब्लिक एड्रेस (बेस64) से पब्लिक की को डिकोड करें
        public_key_der = base64.b64decode(public_address)
        key = ECC.import_key(public_key_der)
        
        # हस्ताक्षर को बेस64 से बाइट्स में डिकोड करें
        signature_bytes = base64.b64decode(signature_b64)
        
        # ट्रांजैक्शन का हैश बनाएँ
        h = hash_transaction(sender, recipient, amount)
        
        # सत्यापनकर्ता (Verifier) बनाएँ
        verifier = DSS.new(key, 'fips-186-3')
        
        # हस्ताक्षर का सत्यापन करें
        verifier.verify(h, signature_bytes)
        
        # यदि सत्यापन सफल होता है, तो कोई त्रुटि नहीं आती है
        return True
        
    except ValueError:
        # यदि हस्ताक्षर गलत है, तो ValueError आती है
        return False
    except Exception as e:
        # अन्य त्रुटियाँ (जैसे अमान्य पता/कुंजी)
        return False
        
# ----------------------------------------------------
# 3. सहायक कार्य (Helper Functions)
# ----------------------------------------------------

def address_from_public_key(public_key_pem):
    """
    PEM पब्लिक की से पब्लिक एड्रेस स्ट्रिंग बनाता है।
    """
    key = ECC.import_key(public_key_pem)
    public_key_der = key.public_key().export_key(format='DER')
    return base64.b64encode(public_key_der).decode('utf-8')

# ----------------------------------------------------
# उपयोग का उदाहरण
# ----------------------------------------------------
# if __name__ == '__main__':
#     # 1. वॉलेट बनाएँ
#     wallet = generate_wallet()
#     print("\n--- नया वॉलेट ---")
#     print(f"एड्रेस: {wallet['public_address']}")
#     # PRIVATE KEY को सुरक्षित रखें! इसे कभी सार्वजनिक न करें।
#     # print(f"प्राइवेट की: {wallet['private_key']}") 

#     # 2. ट्रांजैक्शन डेटा
#     sender_address = wallet['public_address']
#     recipient_address = "SOME_OTHER_ADDRESS"
#     amount_to_send = 10.5
    
#     # 3. ट्रांजैक्शन पर हस्ताक्षर करें
#     signature = sign_transaction(
#         wallet['private_key'], 
#         sender_address, 
#         recipient_address, 
#         amount_to_send
#     )
#     print("\n--- हस्ताक्षर ---")
#     print(f"हस्ताक्षर: {signature}")

#     # 4. हस्ताक्षर सत्यापित करें
#     is_valid = verify_signature(
#         sender_address, # पब्लिक एड्रेस
#         signature, 
#         sender_address, # ट्रांजैक्शन डेटा
#         recipient_address, 
#         amount_to_send
#     )
#     print("\n--- सत्यापन परिणाम ---")
#     print(f"हस्ताक्षर वैध है: {is_valid}") # True आना चाहिए