-- | Multi-lane amalgamation (ported from scripts/forks/amalgamate_all.py, gadget mode).
-- For each agent lane on a gadget, capture its delta, apply it to the gadget
-- integration branch under expected-OID guards, then rewind the lane to base.
-- Plan-only unless --apply. Lanes are ephemeral; integration is truth.
module LambdaScript.Forks.Amalgamate
  ( amalgamateGadget
  ) where

import Control.Monad (forM, when, unless)
import Data.Maybe (catMaybes)

import LambdaScript.Forks.Git
import LambdaScript.Forks.Land (pushRefOf, removeWorktree, shellIn)

amalgamateGadget :: FilePath -> String -> String -> [String] -> Bool -> IO String
amalgamateGadget root gizmo gadget verifyCmds apply = do
  ensureDirs root
  fetch root
  let target = "origin/gadgets/" ++ gizmo ++ "/" ++ gadget ++ "/main"
  okT <- refExists root target
  unless okT (ioError (userError ("missing gadget integration ref: " ++ target)))
  rows <- forM agents (\a -> amalgamateLane root gizmo gadget a target verifyCmds apply)
  let header = "amalgamate-all " ++ gizmo ++ "/" ++ gadget
                 ++ (if apply then " (applied)" else " (plan only; pass --apply)")
  pure (unlines (header : catMaybes rows))

amalgamateLane :: FilePath -> String -> String -> String -> String -> [String] -> Bool -> IO (Maybe String)
amalgamateLane root gizmo gadget agent target verifyCmds apply = do
  let laneBranch = "gadget-agents/" ++ gizmo ++ "/" ++ gadget ++ "/" ++ normalizeAgent agent
      laneRef = "origin/" ++ laneBranch
  ex <- refExists root laneRef
  if not ex
    then pure Nothing
    else do
      base <- mergeBase root target laneRef
      laneCommit <- commit root laneRef
      if null base || base == laneCommit
        then pure (Just ("  " ++ agent ++ ": no lane delta"))
        else if not apply
          then pure (Just ("  " ++ agent ++ ": pending lane work " ++ take 12 laneCommit
                            ++ " (base " ++ take 12 base ++ ")"))
          else applyLane root gizmo gadget agent target laneBranch laneCommit base verifyCmds

applyLane :: FilePath -> String -> String -> String -> String -> String -> String -> String -> [String] -> IO (Maybe String)
applyLane root gizmo gadget agent target laneBranch laneCommit base verifyCmds = do
  -- capture lane delta as a binary patch
  patchRes <- git root ["diff", "--binary", base, "origin/" ++ laneBranch]
  when (gitExit patchRes /= 0) (ioError (userError ("capture failed for lane " ++ laneBranch)))
  let patchText = gitStdout patchRes
      work = forksPath root ["amalgamate-all", normalizeAgent agent ++ "--" ++ gizmo ++ "--" ++ gadget]
  expectedTarget <- commit root target
  removeWorktree root work
  _ <- git root ["worktree", "add", "--detach", work, target]
  applyRes <- gitInput work ["apply", "--3way", "--whitespace=nowarn", "-"] patchText
  if gitExit applyRes /= 0
    then do
      removeWorktree root work
      ioError (userError ("git apply failed for lane " ++ laneBranch ++ ": " ++ gitStderr applyRes))
    else do
      _ <- git work ["add", "-A"]
      status <- gitText work ["status", "--porcelain=v1"] ""
      when (not (null status)) $ do
        _ <- git work
              [ "-c", "user.name=Forks", "-c", "user.email=forks@local"
              , "commit", "-m", "Amalgamate " ++ normalizeAgent agent ++ " into " ++ gizmo ++ "/" ++ gadget ]
        pure ()
      -- verification gate
      mapM_
        (\cmd -> do
            code <- shellIn work cmd
            when (code /= 0) $ do
              removeWorktree root work
              ioError (userError ("verification failed for lane " ++ laneBranch ++ ": " ++ cmd)))
        verifyCmds
      -- OID guard: integration unchanged since capture
      fetch work
      currentTarget <- commit work target
      when (currentTarget /= expectedTarget) $ do
        removeWorktree root work
        ioError (userError ("gadget integration changed before push expected=" ++ take 12 expectedTarget
                             ++ " current=" ++ take 12 currentTarget))
      pushRes <- git work ["push", "origin", "HEAD:" ++ pushRefOf target]
      when (gitExit pushRes /= 0) $ do
        removeWorktree root work
        ioError (userError ("push to integration failed for lane " ++ laneBranch ++ ": " ++ gitStderr pushRes))
      removeWorktree root work
      -- rewind the lane to base, guarded by force-with-lease on the captured lane oid
      rewindRes <- git root
        [ "push", "--force-with-lease=" ++ laneBranch ++ ":" ++ laneCommit
        , "origin", base ++ ":refs/heads/" ++ laneBranch ]
      when (gitExit rewindRes /= 0)
        (ioError (userError ("lane rewind failed (remote moved since capture?) for " ++ laneBranch
                              ++ ": " ++ gitStderr rewindRes)))
      pure (Just ("  " ++ agent ++ ": amalgamated " ++ take 12 laneCommit
                   ++ " -> integration; lane rewound to base " ++ take 12 base))
