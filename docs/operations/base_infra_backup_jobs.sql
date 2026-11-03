/*
  P.08.02 — scheduled backups of base_infra (the books: positions, cash, order ledger), owner's choice 2026-11-03:
  nightly FULL at 02:00 + hourly LOG, compressed, with CHECKSUM, kept 14 days, local folder.

  Apply (idempotent: drops and re-creates the two jobs):
      sqlcmd -S . -E -C -b -i docs\operations\base_infra_backup_jobs.sql      (-C: trust the local certificate)
  The jobs run only while the SQL Server Agent service (SQLSERVERAGENT) runs — see docs/operations/BACKUPS.md.

  Scheduled files go to <default backup folder>\base_infra_scheduled; the 14-day cleanup only looks there, so the
  manual COPY_ONLY backups taken before schema changes (in the backup folder itself) are never deleted by it.
*/
SET NOCOUNT ON;
USE msdb;

DECLARE @dir nvarchar(400) =
    CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS nvarchar(400)) + N'\base_infra_scheduled';
EXEC master.sys.xp_create_subdir @dir;

DECLARE @full nvarchar(max) = N'
DECLARE @dir nvarchar(400) = N''' + @dir + N''';
DECLARE @file nvarchar(400) = @dir + N''\base_infra_FULL_'' + FORMAT(SYSDATETIME(), ''yyyyMMdd_HHmm'') + N''.bak'';
BACKUP DATABASE [base_infra] TO DISK = @file
    WITH COMPRESSION, CHECKSUM, INIT, NAME = N''base_infra full (scheduled)'';
RESTORE VERIFYONLY FROM DISK = @file WITH CHECKSUM;
DECLARE @cut datetime = DATEADD(day, -14, GETDATE());
EXEC master.sys.xp_delete_file 0, @dir, N''bak'', @cut, 0;
EXEC master.sys.xp_delete_file 0, @dir, N''trn'', @cut, 0;';

DECLARE @log nvarchar(max) = N'
DECLARE @file nvarchar(400) = N''' + @dir + N'\base_infra_LOG_'' + FORMAT(SYSDATETIME(), ''yyyyMMdd_HHmm'') + N''.trn'';
BACKUP LOG [base_infra] TO DISK = @file
    WITH COMPRESSION, CHECKSUM, INIT, NAME = N''base_infra log (scheduled)'';';

IF EXISTS (SELECT 1 FROM dbo.sysjobs WHERE name = N'base_infra - full backup (daily 02:00)')
    EXEC dbo.sp_delete_job @job_name = N'base_infra - full backup (daily 02:00)';
IF EXISTS (SELECT 1 FROM dbo.sysjobs WHERE name = N'base_infra - log backup (hourly)')
    EXEC dbo.sp_delete_job @job_name = N'base_infra - log backup (hourly)';

EXEC dbo.sp_add_job @job_name = N'base_infra - full backup (daily 02:00)',
    @description = N'P.08.02: compressed full backup with checksum + verify; deletes scheduled files older than 14 days.';
EXEC dbo.sp_add_jobstep @job_name = N'base_infra - full backup (daily 02:00)', @step_name = N'backup, verify, cleanup',
    @subsystem = N'TSQL', @database_name = N'master', @command = @full;
EXEC dbo.sp_add_jobschedule @job_name = N'base_infra - full backup (daily 02:00)', @name = N'daily 02:00',
    @freq_type = 4, @freq_interval = 1, @active_start_time = 020000;
EXEC dbo.sp_add_jobserver @job_name = N'base_infra - full backup (daily 02:00)';

EXEC dbo.sp_add_job @job_name = N'base_infra - log backup (hourly)',
    @description = N'P.08.02: compressed transaction-log backup with checksum (FULL recovery: keeps the log small).';
EXEC dbo.sp_add_jobstep @job_name = N'base_infra - log backup (hourly)', @step_name = N'log backup',
    @subsystem = N'TSQL', @database_name = N'master', @command = @log;
EXEC dbo.sp_add_jobschedule @job_name = N'base_infra - log backup (hourly)', @name = N'hourly',
    @freq_type = 4, @freq_interval = 1, @freq_subday_type = 8, @freq_subday_interval = 1,
    @active_start_time = 003000;
EXEC dbo.sp_add_jobserver @job_name = N'base_infra - log backup (hourly)';

PRINT N'Jobs created; backups go to ' + @dir;
