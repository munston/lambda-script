module LambdaScript where

import Data.List
import System.Directory
import System.FilePath

import qualified Data.Aeson as Aeson

import Folders.Routes
import LambdaScript.Compiler
import LambdaScript.Core.Diagnostic
import LambdaScript.Paths
import qualified LambdaScript.Gizmo.Manifest as GizmoManifest
import qualified LambdaScript.Gizmo.Runner as GizmoRunner
import qualified LambdaScript.Gizmo.Types as GizmoTypes
import qualified LambdaScript.Forks as Forks


verifiedRoutes :: [VerifiedRoute]
verifiedRoutes =
  [ VerifiedRoute { routeOption = "--list", routeArgs = [], routePrecog = "\\s -> \"--list\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "--self-test", routeArgs = [], routePrecog = "\\s -> \"lambda-script compiler self-test pass\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "--describe", routeArgs = [], routePrecog = "\\s -> \"Haskell LambdaScript compiler\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "parse", routeArgs = [], routePrecog = "\\s -> \"Program\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "check", routeArgs = [], routePrecog = "\\s -> \"OK: no diagnostics\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "emit", routeArgs = [], routePrecog = "\\s -> \"answer = 42\" `isInfixOf` s" }
  , VerifiedRoute { routeOption = "gizmo", routeArgs = [], routePrecog = "\\s -> \"gizmo\" `isInfixOf` s" }
  ]

routeOptouts :: [RouteOptout]
routeOptouts = []

go :: String -> [String] -> IO String
go "--list" [] = pure (show commandList)
go "--list" _ = pure "--list expects no arguments"
go "--describe" [] = pure description
go "--describe" _ = pure "--describe expects no arguments"
go "--self-test" [] = selfTest
go "--self-test" _ = pure "--self-test expects no arguments"
go "parse" (file : rest) = runParse file (elem "--json" rest)
go "parse" _ = pure "usage: parse <file.ls> [--json]"
go "check" [file] = runCheck file
go "check" _ = pure "usage: check <file.ls>"
go "emit" args = runEmit args
go "gizmo" args = runGizmo args
go "forks" args = Forks.run args
go option _ = pure ("unknown lambda-script option: " ++ option)

commandList :: [String]
commandList =
  [ "--list"
  , "--describe"
  , "--self-test"
  , "parse"
  , "check"
  , "emit"
  , "gizmo"
  , "forks"
  ]

description :: String
description =
  unlines
    [ "Haskell LambdaScript compiler (glc rewrite)"
    , "location: projects/lambda-script"
    , "pipeline: parse .ls -> check -> emit Haskell"
    , "status: Core-0 compiler ported from TypeScript glc into Haskell"
    , "next: forks, gizmo, tools, examples corpus, package bridge"
    ]

selfTest :: IO String
selfTest = do
  rootResult <- resolveExamplesRoot
  case rootResult of
    Left err -> pure err
    Right examplesRoot -> selfTestWithExamples examplesRoot

selfTestWithExamples :: FilePath -> IO String
selfTestWithExamples examplesRoot = do
  let hello = examplesRoot </> "hello.ls"
      ffi = examplesRoot </> "ffi_cpp.ls"
  helloExists <- doesFileExist hello
  ffiExists <- doesFileExist ffi
  helloResult <- compileFileToHaskell hello
  ffiResult <- compileFileToHaskell ffi
  let required =
        [ helloExists
        , ffiExists
        , null (compileDiagnostics helloResult)
        , null (compileDiagnostics ffiResult)
        , case compileHaskell helloResult of
            Just hs -> "answer = 42" `isInfixOf` hs
            Nothing -> False
        ]
  if and required
    then
      pure
        ( unlines
            [ "lambda-script compiler self-test pass"
            , "examples: hello.ls, ffi_cpp.ls"
            , "modules: Ast, Program, Parser, Check, Haskell, Compiler"
            ]
        )
    else
      pure
        ( unlines
            ( "lambda-script compiler self-test failed"
                : [ "hello diagnostics: " ++ formatDiagnostics (compileDiagnostics helloResult) | not (null (compileDiagnostics helloResult)) ]
                ++ [ "ffi diagnostics: " ++ formatDiagnostics (compileDiagnostics ffiResult) | not (null (compileDiagnostics ffiResult)) ]
            )
        )

runParse :: FilePath -> Bool -> IO String
runParse file asJson = do
  exists <- doesFileExist file
  if not exists
    then pure ("Error: file not found: " ++ file)
    else do
      source <- readSourceFile file
      let result = parseSource source file
      if not (null (compileDiagnostics result))
        then pure ("Parse errors:\n" ++ formatDiagnostics (compileDiagnostics result))
        else case compileProgram result of
          Nothing -> pure "Parse failed"
          Just program -> pure (show program)

runCheck :: FilePath -> IO String
runCheck file = do
  exists <- doesFileExist file
  if not exists
    then pure ("Error: file not found: " ++ file)
    else do
      source <- readSourceFile file
      let parsed = parseSource source file
      case compileProgram parsed of
        Nothing -> pure ("Check diagnostics:\n" ++ formatDiagnostics (compileDiagnostics parsed))
        Just program ->
          let checked = checkParsed program
          in if null (compileDiagnostics checked)
               then pure "OK: no diagnostics"
               else pure ("Check diagnostics:\n" ++ formatDiagnostics (compileDiagnostics checked))

runEmit :: [String] -> IO String
runEmit args =
  case args of
    file : rest ->
      let target = emitTarget rest
          outFile = emitOut rest
      in do
        result <- compileFileToHaskell file
        if not (null (compileDiagnostics result))
          then pure ("Check diagnostics:\n" ++ formatDiagnostics (compileDiagnostics result))
          else case compileHaskell result of
            Nothing -> pure "Emit failed"
            Just hs ->
              if target == "py" || target == "python"
                then pure "Python emission is unsupported by design. lambda-script emits Haskell only."
                else if target == "hs"
                  then case outFile of
                    Just path -> writeFile path hs >> pure ("Wrote " ++ path)
                    Nothing -> pure hs
                  else pure ("Unknown target: " ++ target)
    _ -> pure "usage: emit <file.ls> --target hs|py [--out <file>]"

runGizmo :: [String] -> IO String
runGizmo args =
  case args of
    ["validate", file] ->
      do
        mval <- Aeson.decodeFileStrict' file :: IO (Maybe Aeson.Value)
        case mval of
          Nothing -> pure ("failed to parse manifest: " ++ file)
          Just val ->
            let issues = GizmoManifest.validateManifest val
             in if null issues
                  then pure "OK: manifest valid"
                  else pure (unlines [GizmoTypes.validationIssuePath i ++ ": " ++ GizmoTypes.validationIssueMessage i | i <- issues])
    ["status", file] ->
      do
        mval <- Aeson.decodeFileStrict' file :: IO (Maybe Aeson.Value)
        case mval of
          Nothing -> pure ("failed to parse manifest: " ++ file)
          Just val ->
            case Aeson.fromJSON val of
              Aeson.Error err -> pure ("manifest decode error: " ++ err)
              Aeson.Success manifest -> pure (show (GizmoManifest.buildStatus manifest))
    ["provision-plan", file] ->
      do
        mval <- Aeson.decodeFileStrict' file :: IO (Maybe Aeson.Value)
        case mval of
          Nothing -> pure ("failed to parse manifest: " ++ file)
          Just val ->
            case Aeson.fromJSON val of
              Aeson.Error err -> pure ("manifest decode error: " ++ err)
              Aeson.Success manifest -> pure (show (GizmoManifest.buildProvisionPlan manifest))
    ("call" : file : gadget : commandName : rest) ->
      do
        let execute = "--exec" `elem` rest
            argPairs = [drop (length "--arg=") t | t <- rest, "--arg=" `isPrefixOf` t]
        mval <- Aeson.decodeFileStrict' file :: IO (Maybe Aeson.Value)
        case mval of
          Nothing -> pure ("failed to parse manifest: " ++ file)
          Just val ->
            let argsMap = GizmoRunner.parseArgPairs argPairs
                plan = GizmoRunner.buildGadgetCommandPlan val gadget commandName argsMap execute
            in do
              code <- GizmoRunner.executeCommandPlan plan
              pure (show plan ++ "\nexit code: " ++ show code)
    _ -> pure "usage: gizmo validate|status|provision-plan <manifest.json> | gizmo call <manifest.json> <gadget> <command> [--arg=name=value] [--exec]"

emitTarget :: [String] -> String
emitTarget rest =
  case dropWhile (/= "--target") rest of
    "--target" : t : _ -> t
    _ -> "hs"

emitOut :: [String] -> Maybe FilePath
emitOut rest =
  case dropWhile (/= "--out") rest of
    "--out" : p : _ -> Just p
    _ -> Nothing