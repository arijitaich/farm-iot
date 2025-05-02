#! /bin/bash
apt update -y
apt install apache2 mysql-client php libapache2-mod-php php-mysql php-cli php-curl php-gd php-mbstring php-xml php-xmlrpc php-soap php-intl php-zip -y

# Install Cloud SQL Auth Proxy
wget https://dl.google.com/cloudsql/cloud-sql-proxy.linux.amd64 -O /usr/local/bin/cloud-sql-proxy
chmod +x /usr/local/bin/cloud-sql-proxy
nohup cloud-sql-proxy greensence:asia-south1:greensens-pdb &
sleep 5

# Restart Apache
systemctl restart apache2

# Create PHP test page
cat <<EOF > /var/www/html/dbtest.php
<?php
\$conn = new mysqli('localhost', 'root', 'green5en5', 'iot_dashboard_v1_04_2025', 3306, '/cloudsql/greensence:asia-south1:greensens-pdb');
if (\$conn->connect_error) { die('Connection failed: ' . \$conn->connect_error); }
echo 'Connected successfully to Cloud SQL!';
?>
EOF
