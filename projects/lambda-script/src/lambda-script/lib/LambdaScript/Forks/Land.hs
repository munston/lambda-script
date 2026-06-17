-- | The single-land engine (ported from scripts/forks/land_json_patch.py).
-- Replays a JSON patch into a candidate worktree on the target ref, gates it
-- ahead-only against the fetched remote (three times), verifies, and pushes.
module LambdaScript.Forks.Land
  ( landJson
  , shellIn
  , syncAgent
  , removeWorktree
  , requireCandidateFresh
  , pushRefOf
  ) where

import Control.Monad (forM_, unless, when)
import System.Directory (doesDirectoryExist, removePathForcibly)

import Data.List (isPrefixOf)

import LambdaScript.Forks.Git
import LambdaScript.Forks.Patch
import LambdaScript.Forks.ProcessResult (printProcessResult, processExitCode, runShellPruned)
import LambdaScript.Forks.ReplayLedger (appendEntry)
import LambdaScript.Forks.Submission (writeSubmission)

-- | Run a shell command in a directory; print a pruned process summary and return
-- the exit code. Successful inner output is collapsed to one status line; failing
-- output is reduced to actionable diagnostics.
shellIn :: FilePath -> String -> IO Int
shellIn dir cmd = do
  result <- runShellPruned dir cmd
  printProcessResult result
  pure (processExitCode result)

-- | Remove a candidate/promotion worktree if present.
removeWorktree :: FilePath -> FilePath -> IO ()
removeWorktree root work = do
  _ <- git root ["worktree", "remove", "--force", work]
  exists <- doesDirectoryExist work
  when exists (removePathForcibly work)
  _ <- git root ["worktree", "prune"]
  pure ()

-- | The load-bearing invariant: remote-first fetch, target is-ancestor HEAD, ahead-only.
requireCandidateFresh :: FilePath -> FilePath -> String -> IO ()
requireCandidateFresh root work targetRef = do
  fetch work
  ok <- refExists root targetRef
  unless ok (ioError (userError ("missing target ref after fetch: " ++ targetRef)))
  anc <- isAncestor work targetRef "HEAD"
  unless anc (ioError (userError (targetRef ++ " is not an ancestor of imported candidate")))
  (ahead, behind) <- aheadBehind work "HEAD" targetRef
  when (ahead <= 0 || behind /= 0)
    (ioError (userError ("imported candidate is not fresh ahead-only against " ++ targetRef
                          ++ ": ahead=" ++ show ahead ++ " behind=" ++ show behind)))

-- | Remote branch a target ref pushes to (strip origin/).
pushRefOf :: String -> String
pushRefOf t
  | "origin/" `isPrefixOf` t = drop (length "origin/") t
  | otherwise = t

-- | Align a repository agent lane to main (even / behind-only only; refuse otherwise).
syncAgent :: FilePath -> String -> IO ()
syncAgent root agent = do
  let branch = agentBranch agent
  exists <- refExists root branch
  if not exists
    then git root ["branch", branch, mainRef] >> pure ()
    else do
      (ahead, behind) <- aheadBehind root branch mainRef
      case classify ahead behind of
        "even" -> pure ()
        "behind-only" -> do
          cur <- currentBranch root
          if cur == branch
            then git root ["reset", "--hard", mainRef] >> pure ()
            else git root ["branch", "-f", branch, mainRef] >> pure ()
        st -> ioError (userError ("refusing to sync " ++ branch ++ "; state=" ++ st))

-- | Land an LS_JSON_PATCH_V1 file onto @targetRef@.
landJson
  :: FilePath        -- ^ repo root
  -> String          -- ^ agent
  -> String          -- ^ target ref (origin/main or a gadget integration ref)
  -> [String]        -- ^ verification commands (manifest profile); run in the candidate worktree
  -> FilePath        -- ^ patch file
  -> Bool            -- ^ no-sync (skip repo agent lane sync on a main land)
  -> IO String
landJson root agent targetRef verifyCmds patchFile noSync = do
  ensureDirs root
  fetch root
  okT <- refExists root targetRef
  unless okT (ioError (userError ("missing target ref: " ++ targetRef)))
  parsed <- loadPatch patchFile
  patch <- either (\e -> ioError (userError ("patch parse failed: " ++ e))) pure parsed

  let work = forksPath root ["worktrees", normalizeAgent agent ++ "-candidate"]
  removeWorktree root work
  _ <- git root ["worktree", "add", "--detach", work, targetRef]
  applyFileOps work patch
  -- Record the landed payload into the committed replay ledger so the work is
  -- preserved (and later audited as materialised) independent of the lane.
  _ <- appendEntry work agent (patchValue patch) targetRef
  _ <- git work ["add", "-A"]
  status <- gitText work ["status", "--porcelain=v1"] ""
  when (not (null status)) $ do
    let msg = if null (patchTitle patch) then ("Land " ++ normalizeAgent agent ++ " patch") else patchTitle patch
    _ <- git work ["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", msg]
    pure ()

  requireCandidateFresh root work targetRef
  submChanged <- changedFiles work "HEAD" targetRef
  (submAhead, submBehind) <- aheadBehind work "HEAD" targetRef
  writeSubmission root agent targetRef submChanged submAhead submBehind
  forM_ verifyCmds $ \cmd -> do
    code <- shellIn work cmd
    when (code /= 0) (ioError (userError ("verification failed: " ++ cmd)))
  requireCandidateFresh root work targetRef

  let pr = pushRefOf targetRef
  _ <- git work ["push", "--dry-run", "origin", "HEAD:" ++ pr]
  pushRes <- git work ["push", "origin", "HEAD:" ++ pr]
  when (gitExit pushRes /= 0) (ioError (userError ("push to " ++ pr ++ " failed: " ++ gitStderr pushRes)))
  fetch root

  when (targetRef == mainRef && not noSync) (forM_ agents (syncAgent root))
  pure ("landed " ++ normalizeAgent agent ++ " files=" ++ show (length (patchFiles patch)) ++ " -> " ++ pr)
