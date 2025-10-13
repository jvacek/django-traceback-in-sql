-- MySQL initialization script
-- Grants permissions for test database creation

-- Grant all privileges on test databases to testuser
GRANT ALL PRIVILEGES ON `test_%`.* TO 'testuser'@'%';
GRANT ALL PRIVILEGES ON `django_traceback_in_sql_test`.* TO 'testuser'@'%';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;
