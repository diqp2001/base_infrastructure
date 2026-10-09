-- Create the application database if missing (never drops or recreates it).
IF DB_ID(N'$(DB)') IS NULL
    CREATE DATABASE [$(DB)];
GO
