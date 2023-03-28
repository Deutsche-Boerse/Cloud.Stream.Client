#!/bin/sh

# add a new non-root user for better security
groupadd --gid ${USER_GID} ${USERNAME}
useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}
echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME}
chmod 0440 /etc/sudoers.d/${USERNAME}

# setup proxy settings
echo "export HTTP_PROXY=${HTTP_PROXY}" >> /home/${USERNAME}/.bashrc
echo "export HTTPS_PROXY=${HTTPS_PROXY}" >> /home/${USERNAME}/.bashrc
echo "export NO_PROXY=${NO_PROXY}" >> /home/${USERNAME}/.bashrc
echo "export http_proxy=${HTTP_PROXY}" >> /home/${USERNAME}/.bashrc
echo "export https_proxy=${HTTPS_PROXY}" >> /home/${USERNAME}/.bashrc
echo "export no_proxy=${NO_PROXY}" >> /home/${USERNAME}/.bashrc


# Change ownership and group of files in home and app directory of user
chown -R ${USERNAME} /home/${USERNAME} 2>&1 > /dev/null
chgrp -R ${USERNAME} /home/${USERNAME} 2>&1 > /dev/null

cd ${WORK_DIR}
pip install --no-cache-dir -r ${PYTHON_REQ}
sudo ldconfig -v
sudo -u ${USERNAME} /bin/bash