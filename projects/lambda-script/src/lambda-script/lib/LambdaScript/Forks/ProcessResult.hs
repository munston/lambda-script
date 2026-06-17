-- | Pruned process-result summaries for nested command execution.
--
-- The purpose is to make successful inner tools cheap to report while preserving
-- actionable diagnostics when a process fails. Successful output is discarded by
-- default; failing output is reduced to lines near error markers, with a bounded
-- fallback tail when no marker is found.
module LambdaScript.Forks.ProcessResult
  ( ProcessResult(..)
  , runShellPruned
  , processExitCode
  , processSucceeded
  , renderProcessResult
  , printProcessResult
  , pruneProcessText
  ) where

import Data.Char (isSpace, toLower)
import Data.List (isInfixOf, nub, sort)
import System.Exit (ExitCode(..))
import System.Process (CreateProcess(..), readCreateProcessWithExitCode, shell)

data ProcessResult =
  ProcessResult String String Int String String String
  deriving (Eq, Show)

runShellPruned :: FilePath -> String -> IO ProcessResult
runShellPruned dir command = do
  (code, out, err) <- readCreateProcessWithExitCode (shell command) { cwd = Just dir } ""
  let exitCode = exitCodeInt code
      label = inferLabel command
      summary = if exitCode == 0 then "" else pruneProcessText (out ++ "\n" ++ err)
  pure (ProcessResult label command exitCode out err summary)

processExitCode :: ProcessResult -> Int
processExitCode (ProcessResult _ _ code _ _ _) = code

processSucceeded :: ProcessResult -> Bool
processSucceeded result = processExitCode result == 0

renderProcessResult :: ProcessResult -> String
renderProcessResult (ProcessResult label _ code _ _ summary)
  | code == 0 = label ++ ": ok."
  | null summary = label ++ ": failed (exit " ++ show code ++ ")."
  | otherwise = label ++ ": failed (exit " ++ show code ++ ").\n" ++ indent summary

printProcessResult :: ProcessResult -> IO ()
printProcessResult = putStrLn . renderProcessResult

pruneProcessText :: String -> String
pruneProcessText text =
  let ls = filter (not . all isSpace) (lines text)
      windows = diagnosticWindows ls
      selected = if null windows then fallbackLines ls else windows
  in unlines (take maxLines (map trimLine selected))

diagnosticWindows :: [String] -> [String]
diagnosticWindows ls =
  let indexed = zip [0 :: Int ..] ls
      hits = [ i | (i, line) <- indexed, isDiagnosticLine line ]
      wanted = sort (nub (concatMap windowAround hits))
  in [ line | (i, line) <- indexed, i `elem` wanted ]

windowAround :: Int -> [Int]
windowAround i = filter (>= 0) [i - 1, i, i + 1, i + 2]

fallbackLines :: [String] -> [String]
fallbackLines ls = drop (max 0 (length ls - fallbackCount)) ls

isDiagnosticLine :: String -> Bool
isDiagnosticLine line =
  let lower = map toLower line
  in any (`isInfixOf` lower) diagnosticMarkers

diagnosticMarkers :: [String]
diagnosticMarkers =
  [ "error:"
  , "fatal:"
  , "traceback"
  , "assertionerror"
  , "exception"
  , "cabal-"
  , "ghc-"
  , "ghc:"
  , "npm err"
  , "failed"
  , "not found"
  , "cannot"
  , "refusing"
  , "undefined"
  , "parse error"
  , "type error"
  ]

inferLabel :: String -> String
inferLabel command =
  let lower = map toLower command
  in if "cabal" `isInfixOf` lower || "ghc" `isInfixOf` lower
       then "haskell tool"
       else if "npm" `isInfixOf` lower || "node" `isInfixOf` lower
         then "node tool"
         else if "python" `isInfixOf` lower || "py " `isInfixOf` lower
           then "python tool"
           else if "git" `isInfixOf` lower
             then "git"
             else "process"

exitCodeInt :: ExitCode -> Int
exitCodeInt ExitSuccess = 0
exitCodeInt (ExitFailure n) = n

indent :: String -> String
indent = unlines . map ("  " ++) . lines

trimLine :: String -> String
trimLine line =
  let compact = trimRight line
  in if length compact <= maxWidth then compact else take (maxWidth - 3) compact ++ "..."

trimRight :: String -> String
trimRight = reverse . dropWhile isSpace . reverse

maxLines :: Int
maxLines = 24

fallbackCount :: Int
fallbackCount = 12

maxWidth :: Int
maxWidth = 220
