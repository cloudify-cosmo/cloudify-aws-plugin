# https://github.com/tomrittervg/decrypt-windows-ec2-passwd/blob/master/decrypt-windows-ec2-passwd.py

import base64
import binascii


def pkcs1_unpad(text):
    # From http://kfalck.net/2011/03/07/decoding-pkcs1-padding-in-python
    if len(text) > 0 and text[0] == '\x02':
        # Find end of padding marked by nul
        pos = text.find('\x00')
        if pos > 0:
            return text[pos + 1:]
    return None


def long_to_bytes(val, endianness='big'):
    # From http://stackoverflow.com/questions/8730927/
    # convert-python-long-int-to-fixed-size-byte-array

    # one (1) hex digit per four (4) bits
    try:
        # Python < 2.7 doesn't have bit_length =(
        width = val.bit_length()
    except Exception:
        width = len(val.__hex__()[2:-1]) * 4

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = binascii.unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s


def decrypt_password(rsa_key, password):
    # Undo the whatever-they-do to the ciphertext to get the integer
    encryptedData = base64.b64decode(password.encode('utf-8'))
    ciphertext = int(binascii.hexlify(encryptedData), 16)

    # Decrypt it
    plaintext = rsa_key.decrypt(ciphertext)

    # This is the annoying part.  long -> byte array
    decryptedData = long_to_bytes(plaintext)
    # Now Unpad it
    unpaddedData = pkcs1_unpad(decryptedData)

    # Done
    return unpaddedData
