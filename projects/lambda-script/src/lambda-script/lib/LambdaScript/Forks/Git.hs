-- | Foundational git layer for the forks port (ported from scripts/forks/forks.py).
--
-- This is the foxhub seam: every git interaction goes through here against
-- @origin/<ref>@, so the remote (GitHub today, foxhub later) stays abstract.
-- See docs/forks/AMALGAMATION_STATE_MACHINE.md for the contract this serves.
module LambdaScript.Forks.Git
  ( GitResult(..)
  , agents
  , mainRef
  , forksDir
  , snapshotDirs
  , run
  , git
  , gitInput
  , gitText
  , repoRoot
  , ensureDirs
  , forksPath
  , normalizeAgent
  , agentBranch
  , refExists
  , currentBranch
  , commit
  , shortCommit
  , treeHash
  , mergeBase
  , aheadBehind
  , classify
  , changedFiles
  , isAncestor
  , fetch
  , fetchMain
  , nowIso
  , trim
  ) where

import Data.Char (isSpace)
import Data.List (dropWhileEnd, isPrefixOf)
import Data.Time.Clock (getCurrentTime)
import Data.Time.Format.ISO8601 (iso8601Show)
import System.Directory (createDirectoryIfMissing)
import System.Exit (ExitCode(..))
import System.FilePath ((</>))
import System.Process (CreateProcess(..), proc, readCreateProcessWithExitCode)

-- | The default coordination agents (repository lanes).
agents :: [String]
agents = ["ed", "edd", "eddy", "guy"]

-- | Repository truth ref. All single-land/promote operations are remote-first against this.
mainRef :: String
mainRef = "origin/main"

forksDir :: FilePath
forksDir = ".forks"

snapshotDirs :: [FilePath]
snapshotDirs = ["patches", "candidates", "receipts", "worktrees", "snapshots", "conflicts", "ships"]

-- | Result of a subprocess: normalized exit code plus captured streams.
data GitResult =
  GitResult
    { gitExit :: Int
    , gitStdout :: String
    , gitStderr :: String
    }
  deriving (Eq, Show)

-- | Run an arbitrary command in a working directory.
run :: FilePath -> [String] -> IO GitResult
run cwdPath (cmd : args) = do
  (code, out, err) <- readCreateProcessWithExitCode (proc cmd args) { cwd = Just cwdPath } ""
  let n = case code of
            ExitSuccess -> 0
            ExitFailure c -> c
  pure (GitResult n out err)
run _ [] = pure (GitResult 1 "" "empty command")

-- | Run git in @root@.
git :: FilePath -> [String] -> IO GitResult
git root args = run root ("git" : args)

-- | Run git with stdin text (e.g. @git apply -@).
gitInput :: FilePath -> [String] -> String -> IO GitResult
gitInput root args input = do
  (code, out, err) <- readCreateProcessWithExitCode (proc "git" args) { cwd = Just root } input
  let n = case code of
            ExitSuccess -> 0
            ExitFailure c -> c
  pure (GitResult n out err)

-- | Run git, returning trimmed stdout, or @def@ on non-zero exit.
gitText :: FilePath -> [String] -> String -> IO String
gitText root args def = do
  r <- git root args
  pure (if gitExit r /= 0 then def else trim (gitStdout r))

trim :: String -> String
trim = dropWhileEnd isSpace . dropWhile isSpace

-- | The repository top level (errors if not in a git repo).
repoRoot :: IO FilePath
repoRoot = do
  (code, out, _) <- readCreateProcessWithExitCode (proc "git" ["rev-parse", "--show-toplevel"]) ""
  case code of
    ExitSuccess -> pure (trim out)
    ExitFailure _ -> ioError (userError "forks: not inside a git repository")

-- | Ensure the @.forks/<dir>@ scaffold exists.
ensureDirs :: FilePath -> IO ()
ensureDirs root = mapM_ (\d -> createDirectoryIfMissing True (root </> forksDir </> d)) snapshotDirs

-- | A path under @.forks/@.
forksPath :: FilePath -> [FilePath] -> FilePath
forksPath root parts = foldl (</>) (root </> forksDir) parts

-- | Reduce an agent reference to a bare agent name (strips origin\/ and agents\/ prefixes).
normalizeAgent :: String -> String
normalizeAgent agent =
  let name0 = map (\c -> if c == '\\' then '/' else c) (trim agent)
      name1 = stripPfx "origin/" name0
      name2 = stripPfx "agents/" name1
  in if null name2 || '/' `elem` name2
       then error ("invalid agent name: " ++ agent)
       else name2
  where
    stripPfx p s = if p `isPrefixOf` s then drop (length p) s else s

agentBranch :: String -> String
agentBranch agent = "agents/" ++ normalizeAgent agent

refExists :: FilePath -> String -> IO Bool
refExists root ref = do
  r <- git root ["rev-parse", "--verify", "--quiet", ref]
  pure (gitExit r == 0)

currentBranch :: FilePath -> IO String
currentBranch root = gitText root ["branch", "--show-current"] ""

-- | Resolve a ref to a full commit oid (errors if unresolvable).
commit :: FilePath -> String -> IO String
commit root ref = do
  v <- gitText root ["rev-parse", ref] ""
  if null v then ioError (userError ("cannot resolve ref: " ++ ref)) else pure v

shortCommit :: FilePath -> String -> IO String
shortCommit root ref = gitText root ["rev-parse", "--short", ref] ""

treeHash :: FilePath -> String -> IO String
treeHash root ref = do
  v <- gitText root ["rev-parse", ref ++ "^{tree}"] ""
  if null v then ioError (userError ("cannot resolve tree for ref: " ++ ref)) else pure v

mergeBase :: FilePath -> String -> String -> IO String
mergeBase root left right = gitText root ["merge-base", left, right] ""

-- | @(ahead, behind)@ of @ref@ relative to @base@ (mirrors forks.py left-right semantics).
aheadBehind :: FilePath -> String -> String -> IO (Int, Int)
aheadBehind root ref base = do
  txt <- gitText root ["rev-list", "--left-right", "--count", base ++ "..." ++ ref] ""
  case words txt of
    [behindStr, aheadStr] -> pure (readInt aheadStr, readInt behindStr)
    _ -> pure (0, 0)
  where
    readInt s = case reads s of
      [(n, _)] -> n
      _ -> 0

-- | Classify an ahead/behind pair: even | behind-only | ahead-only | diverged.
classify :: Int -> Int -> String
classify ahead behind
  | ahead == 0 && behind == 0 = "even"
  | ahead == 0 && behind > 0 = "behind-only"
  | ahead > 0 && behind == 0 = "ahead-only"
  | otherwise = "diverged"

-- | @diff --name-status base...ref@ as @(status, path)@ pairs.
changedFiles :: FilePath -> String -> String -> IO [(String, String)]
changedFiles root ref base = do
  txt <- gitText root ["diff", "--name-status", base ++ "..." ++ ref] ""
  pure [ (head parts, last parts)
       | line <- lines txt
       , let parts = splitTab line
       , length parts >= 2
       ]
  where
    splitTab s = case break (== '\t') s of
      (a, '\t' : rest) -> a : splitTab rest
      (a, _) -> [a]

-- | Is @anc@ an ancestor of @desc@ (the ahead-only/freshness primitive).
isAncestor :: FilePath -> String -> String -> IO Bool
isAncestor root anc desc = do
  r <- git root ["merge-base", "--is-ancestor", anc, desc]
  pure (gitExit r == 0)

-- | Fetch and prune origin (remote-first invariant).
fetch :: FilePath -> IO ()
fetch root = do
  _ <- git root ["fetch", "--prune", "origin"]
  pure ()

-- | Fetch and require origin/main to exist afterward.
fetchMain :: FilePath -> IO ()
fetchMain root = do
  fetch root
  ok <- refExists root mainRef
  if ok then pure () else ioError (userError ("missing " ++ mainRef ++ "; fetch did not produce it"))
