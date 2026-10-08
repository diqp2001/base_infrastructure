-- Read-only login for the monitoring dashboard: db_datareader only, writes explicitly denied.
IF SUSER_ID(N'$(RO_USER)') IS NULL
    CREATE LOGIN [$(RO_USER)] WITH PASSWORD = N'$(RO_PWD)', CHECK_POLICY = ON, DEFAULT_DATABASE = [$(DB)];
ELSE
    ALTER LOGIN [$(RO_USER)] WITH PASSWORD = N'$(RO_PWD)';
GO
USE [$(DB)];
GO
IF USER_ID(N'$(RO_USER)') IS NULL
    CREATE USER [$(RO_USER)] FOR LOGIN [$(RO_USER)];
GO
ALTER ROLE db_datareader ADD MEMBER [$(RO_USER)];
GO
DENY INSERT, UPDATE, DELETE, ALTER, EXECUTE, REFERENCES TO [$(RO_USER)];
GO
