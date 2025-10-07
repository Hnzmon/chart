-- 初期ユーザー設定
CREATE USER IF NOT EXISTS 'stock_user'@'%' IDENTIFIED WITH mysql_native_password BY 'stock_password';
GRANT ALL PRIVILEGES ON chart.* TO 'stock_user'@'%';

-- rootユーザーの認証プラグインを変更（GUI接続用）
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'example';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'example';

FLUSH PRIVILEGES;