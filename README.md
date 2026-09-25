# What is the OTA update ?

It is the process that has capability to update its clients' root file system, firmware (software with low-level control for hardware), and applications remotely through a wireless network or internet.

## 2 attacks that OTA firmware updates might prone

- Firmware Injection Attack

**Attacker's possible action :** Attackers establish their own unauthorized firmware update (manifest + Merkle tree) and exchange them with client on behalf of the server, replacing an original firmware update. Using their malicious and controllable firmware update, they could access to clients and manipulate the resource of those clients. To achieve their goals, the attackers would find MQTT credentials, understand the paradigm of communication between server and client, and create their own firmware update imitating the system's firmware update with an artificial manifest.

**Which part of the update process might be affected :** Entire process is susceptible to this kind of attack. As the attacker's malicious firmware would bypass the verification of firmware update and the client consider normally the affected firmware update, the parts of process on client including manifest and chunk transmission, chunk reconstruction, firmware installation, and firmware execution would be affected. Beyond the client, the part of process creating Merkle tree and chunks would be controlled by the attackers. Moreover, the normal updates not by the attackers after the attack can be affected due to manifest versioning.

**Would my implementation prevent from the attack :** My initial implementation cannot prevent from this kind of attack, since the broker transmitting the update in my implementation has not credentials and there is no verification to determine whether the update is sent by an authorized source (the server). The Merkle tree provides integrity verification by detecting whether any part of the firmware update has been modified or corrupted. However, it does not verify the origin or authenticity of the update.

**Required additional protection :** Two additional protection should be considered in the updating process. First, broker credentials should be configured, and both the OTA client and server should use their assigned credentials to authenticate when connecting to the MQTT broker. This prevents unauthorized entities from connecting to the broker and publishing or subscribing to OTA messages without valid credentials. Second, the manifest of update should be digitally signed by the authorized OTA server. The OTA server send the manifest and a digital signature encoded by the private key. The client verifies the signature using the server's trusted public key which is securely stored on the client before accepting the update. It would be better not to send the public key with signature, since attackers can replace all of the public key, signature, and manifest.

- Attack 2
Attacker's possible action
Which part of the update process might be affected
The implementation would prevent from the attack
Required additional protection