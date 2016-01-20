########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Taken from https://github.com/tomrittervg/decrypt-windows-ec2-passwd
import base64
import binascii

from Crypto.PublicKey import RSA

from cloudify.exceptions import NonRecoverableError


def _pkcs1_unpad(text):
    if len(text) > 0 and text[0] == '\x02':
        # Find end of padding marked by nul
        pos = text.find('\x00')
        if pos > 0:
            return text[pos+1:]
    return None


def _long_to_bytes(val, endianness='big'):
    # one (1) hex digit per four (4) bits
    width = val.bit_length()
    width += 8 - ((width % 8) or 8)
    fmt = '%%0%dx' % (width // 4)
    s = binascii.unhexlify(fmt % val)
    if endianness == 'little':
        s = s[::-1]

    return s


def _decrypt_password(rsa_key, password):
    encrypted_data = base64.b64decode(password)
    cipher_text = int(binascii.hexlify(encrypted_data), 16)

    plaintext = rsa_key.decrypt(cipher_text)

    decrypted_data = _long_to_bytes(plaintext)
    unpadded_data = _pkcs1_unpad(decrypted_data)

    return unpadded_data


def get_windows_passwd(private_key_path, password_data):

    key_file = open(private_key_path)
    key_lines = key_file.readlines()
    try:
        key = RSA.importKey(key_lines)
    except ValueError as e:
        raise NonRecoverableError(
            'Could not import SSH Key: {0}'.format(str(e)))

    password = _decrypt_password(key, password_data)

    return password
