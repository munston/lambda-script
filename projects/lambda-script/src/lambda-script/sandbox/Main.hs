module Main where

import Control.Exception (IOException, catch)
import System.Directory (doesFileExist, getCurrentDirectory)
import System.Environment (getArgs)
import System.Exit (ExitCode(..), exitWith)
import System.FilePath ((</>))
import System.Info (os)
import System.Process (rawSystem)

import LambdaScript.Sandbox.Command
  ( OnepushOptions
  , SandboxCommand(..)
  , helpText
  , optInitFromDir
  , optShip
  , parseCommand
  )
import LambdaScript.Sandbox.Config
  ( SandboxConfig
  , cfgButton
  , cfgToolRoot
  , loadConfig
  )

main :: IO ()
main = do
  args <- getArgs
  result <- (Right <$> dispatch args) `catch` (pure . Left)
  case result of
    Right ExitSuccess -> pure ()
    Right code -> exitWith code
    Left e -> putStrLn ("sandbox: " ++ show (e :: IOException)) >> exitWith (ExitFailure 1)

dispatch :: [String] -> IO ExitCode
dispatch args = do
  cwd <- getCurrentDirectory
  cfg <- loadConfig cwd
  case parseCommand args of
    Right SandboxHelp -> usage ExitSuccess
    Right (SandboxOnepush opts) -> runButton cfg (onepushArgs opts)
    Right (SandboxLand patch) -> runLand cfg patch
    Left _ -> putStr "sandbox: unsupported command. Use `cabal run sandbox -- help`.\n" >> pure (ExitFailure 2)

onepushArgs :: OnepushOptions -> [String]
onepushArgs opts =
  shipArg ++ initArg
  where
    shipArg = if optShip opts then ["--ship"] else []
    initArg =
      case optInitFromDir opts of
        Nothing -> []
        Just dir -> ["--init-from-dir", dir]

runButton :: SandboxConfig -> [String] -> IO ExitCode
runButton cfg xs = do
  let exe = cfgToolRoot cfg </> ("onepush-" ++ cfgButton cfg ++ ".bat")
  requireFile exe
  runTrusted exe xs

runLand :: SandboxConfig -> FilePath -> IO ExitCode
runLand cfg patch = do
  requireFile patch
  let exe = cfgToolRoot cfg </> "land-anything.bat"
  requireFile exe
  runTrusted exe [patch]

runTrusted :: FilePath -> [String] -> IO ExitCode
runTrusted exe xs
  | os == "mingw32" = rawSystem "cmd" (["/c", "call", exe] ++ xs)
  | otherwise = rawSystem exe xs

requireFile :: FilePath -> IO ()
requireFile path = do
  ok <- doesFileExist path
  if ok then pure () else ioError (userError ("missing required file: " ++ path))

usage :: ExitCode -> IO ExitCode
usage code = putStr helpText >> pure code
