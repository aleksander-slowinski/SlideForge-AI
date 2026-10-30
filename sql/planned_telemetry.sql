USE SlideForgeDB;
GO

-- SlideForge 1.1: preserves GenerationMode ('gemini'/'demo') and all classic rows.
IF COL_LENGTH('dbo.GenerationRun','GenerationStrategy') IS NULL
BEGIN
    ALTER TABLE dbo.GenerationRun ADD GenerationStrategy VARCHAR(16) NOT NULL
        CONSTRAINT DF_GenerationRun_GenerationStrategy DEFAULT ('classic');
    ALTER TABLE dbo.GenerationRun ADD CONSTRAINT CK_GenerationRun_GenerationStrategy
        CHECK (GenerationStrategy IN ('classic','planned'));
END;
GO
IF COL_LENGTH('dbo.GenerationRun','CheckpointFingerprint') IS NULL
    ALTER TABLE dbo.GenerationRun ADD CheckpointFingerprint CHAR(64) NULL;
IF COL_LENGTH('dbo.GenerationRun','BatchSize') IS NULL
    ALTER TABLE dbo.GenerationRun ADD BatchSize INT NULL;
IF COL_LENGTH('dbo.GenerationRun','ApiCallCount') IS NULL
    ALTER TABLE dbo.GenerationRun ADD ApiCallCount INT NULL;
IF COL_LENGTH('dbo.GenerationRun','CheckpointHitCount') IS NULL
    ALTER TABLE dbo.GenerationRun ADD CheckpointHitCount INT NULL;
GO

IF OBJECT_ID('dbo.PlannedBatchExecution','U') IS NULL
BEGIN
    CREATE TABLE dbo.PlannedBatchExecution (
        RunID BIGINT NOT NULL,
        BatchIndex INT NOT NULL,
        SlideFrom INT NOT NULL,
        SlideTo INT NOT NULL,
        Outcome VARCHAR(16) NOT NULL,
        DurationMs BIGINT NOT NULL,
        ApiCalls INT NOT NULL,
        LLMDurationMs BIGINT NULL,
        PromptTokens INT NULL,
        OutputTokens INT NULL,
        ThinkingTokens INT NULL,
        TotalTokens INT NULL,
        LastHttpStatus INT NULL,
        RecordedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_PlannedBatchExecution_Recorded DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_PlannedBatchExecution PRIMARY KEY (RunID, BatchIndex),
        CONSTRAINT FK_PlannedBatchExecution_GenerationRun FOREIGN KEY (RunID)
            REFERENCES dbo.GenerationRun(RunID),
        CONSTRAINT CK_PlannedBatchExecution_Outcome CHECK (Outcome IN ('CHECKPOINT','GENERATED','FAILED')),
        CONSTRAINT CK_PlannedBatchExecution_Slides CHECK (BatchIndex > 0 AND SlideFrom > 0 AND SlideTo >= SlideFrom),
        CONSTRAINT CK_PlannedBatchExecution_Counters CHECK (DurationMs >= 0 AND ApiCalls >= 0)
    );
END;
GO

-- Retain original measures and columns from Sprint 9.3; append new strategy fields.
CREATE OR ALTER VIEW dbo.vw_GenerationAnalytics
AS
SELECT
    g.RunID, g.StartedAtUtc, g.FinishedAtUtc,
    CAST(g.StartedAtUtc AS DATE) AS GenerationDateUtc,
    g.GenerationMode, g.GenerationStrategy, g.Topic,
    g.RequestedSlides, g.GeneratedSlides, g.Status, g.ErrorCode,
    g.DurationMs,
    CAST(g.DurationMs / 1000.0 AS DECIMAL(12,3)) AS DurationSeconds,
    CAST(CASE WHEN LEFT(LTRIM(COALESCE(g.Topic, N'')),6) = N'[TEST]'
        THEN 1 ELSE 0 END AS BIT) AS IsTest,
    q.QualityScore,
    q.WarningCount AS QualityWarningCount,
    q.ErrorCount AS QualityErrorCount,
    q.InfoCount AS QualityInfoCount,
    q.QualityEngineVersion, q.EvaluatedAtUtc,
    g.ModelName, g.ThinkingLevel,
    g.LLMDurationMs, g.ValidationDurationMs, g.PptxDurationMs,
    g.PromptTokens, g.OutputTokens, g.ThinkingTokens, g.TotalTokens,
    g.CheckpointFingerprint, g.BatchSize,
    g.ApiCallCount, g.CheckpointHitCount
FROM dbo.GenerationRun AS g
LEFT JOIN dbo.GenerationQuality AS q ON g.RunID = q.RunID;
GO

CREATE OR ALTER VIEW dbo.vw_PlannedBatchAnalytics
AS
SELECT
    b.RunID, b.BatchIndex, b.SlideFrom, b.SlideTo,
    b.Outcome, b.DurationMs,
    CAST(b.DurationMs / 1000.0 AS DECIMAL(12,3)) AS DurationSeconds,
    b.ApiCalls, b.LLMDurationMs,
    b.PromptTokens, b.OutputTokens, b.ThinkingTokens, b.TotalTokens,
    b.LastHttpStatus, b.RecordedAtUtc
FROM dbo.PlannedBatchExecution AS b;
GO

SELECT TOP (5) RunID, GenerationStrategy, Status, ApiCallCount,
    CheckpointHitCount, CheckpointFingerprint
FROM dbo.vw_GenerationAnalytics ORDER BY RunID DESC;
GO
