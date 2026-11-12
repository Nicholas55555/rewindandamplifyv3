"""Save your IBM Quantum account on this computer, once.

Run it yourself in a terminal. The API key is typed at a hidden prompt, so it never appears on screen, in a file in
this repository, or in any log. Qiskit stores it in its own account file in your home folder (~/.qiskit), which is
never part of this repository.

    python tools/save_ibm_account.py

Find your API key and instance on https://quantum.cloud.ibm.com (Dashboard: "API key", and "Instances" for the CRN).
The instance can be left blank; Qiskit then looks through every instance your key can use.
"""

import getpass

from qiskit_ibm_runtime import QiskitRuntimeService


def main() -> None:
    print("IBM Quantum account setup. The key stays on this computer and is not shown as you type or paste it.")
    token = getpass.getpass("API key (hidden; paste, then press Enter): ").strip()
    if not token:
        print("No key entered, so nothing was saved. The project still runs fully on simulators.")
        return
    instance = input("Instance CRN (optional; press Enter to skip): ").strip() or None
    QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token=token, instance=instance,
                                      set_as_default=True, overwrite=True)
    del token
    print("Saved. Checking which devices this account can use ...")
    service = QiskitRuntimeService()
    names = [b.name for b in service.backends(simulator=False, operational=True)]
    print("Devices available:", ", ".join(names) if names else "none listed")
    print("Done. You can close this tab.")


if __name__ == "__main__":
    main()
