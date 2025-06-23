"""
wsl.exe --install 
wsl --version
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --install Ubuntu
4. Après le redémarrage

Ubuntu va se lancer automatiquement
Il va vous demander de créer un nom d'utilisateur et mot de passe Linux
Créez-les (ils peuvent être différents de votre compte Windows)
Create a default Unix user account: phildiquinzio
password:phildiquinzio
5. Une fois Ubuntu configuré
Vous pourrez alors :
powershellwsl
Et vous serez dans l'environnement Ubuntu où vous pourrez installer nvm, Node.js et Claude Code !


installation github cli
sudo snap install gh
echo 'export PATH="/snap/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
gh --version
"""