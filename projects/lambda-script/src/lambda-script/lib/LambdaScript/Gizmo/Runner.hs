module LambdaScript.Gizmo.Runner where

import qualified Data.Aeson as Aeson
import qualified Data.Map.Strict as Map
import qualified Data.Set as Set
import Data.Char
import Data.List
import System.Exit
import System.Process

import LambdaScript.Gizmo.Manifest
import qualified LambdaScript.Gizmo.Types as GizmoTypes

parseArgPairs :: [String] -> Map.Map String String
parseArgPairs values =
  Map.fromList (map parseArgPair values)
  where
    parseArgPair item =
      case break (== '=') item of
        (_, []) -> error ("expected --arg name=value, got: " ++ item)
        (name, '=' : value)
          | null name -> error ("expected --arg name=value, got: " ++ item)
          | not (isSafeArgName name) -> error ("unsafe argument name: " ++ name)
          | null value -> error ("empty argument value for " ++ name)
          | otherwise -> (name, value)
        _ -> error ("expected --arg name=value, got: " ++ item)

    isSafeArgName :: String -> Bool
    isSafeArgName name =
      case name of
        c : rest -> (isAlpha c || c == '_') && all isArgNameChar rest
        _ -> False

    isArgNameChar c = isAlphaNum c || c == '_' || c == '-'

buildGadgetCommandPlan ::
  Aeson.Value ->
  String ->
  String ->
  Map.Map String String ->
  Bool ->
  GizmoTypes.GizmoCommandPlan
buildGadgetCommandPlan manifestInput gadgetName commandName args execute =
  let manifest = ensureManifestValid manifestInput
      gadget =
        case Map.lookup gadgetName (GizmoTypes.gizmoManifestGadgets manifest) of
          Just found -> found
          Nothing -> error ("unknown gadget: " ++ gadgetName)
      template =
        case Map.lookup commandName (GizmoTypes.gadgetManifestCommands gadget) of
          Just found -> found
          Nothing -> error ("unknown command for gadget " ++ gadgetName ++ ": " ++ commandName)
      required = placeholders template
      supplied = Set.toAscList (Map.keysSet args)
      missing = filter (\name -> not (Map.member name args)) required
      unused = filter (`notElem` required) supplied
   in if not (null missing)
        then error ("missing command args: " ++ intercalate ", " missing)
        else if not (null unused)
          then error ("unused command args: " ++ intercalate ", " unused)
          else
            GizmoTypes.GizmoCommandPlan
              { GizmoTypes.gizmoCommandPlanFormat = GizmoTypes.gizmoCommandPlanFormatTag
              , GizmoTypes.gizmoCommandPlanGizmo = GizmoTypes.gizmoManifestName manifest
              , GizmoTypes.gizmoCommandPlanScope = "gadget"
              , GizmoTypes.gizmoCommandPlanName = gadgetName
              , GizmoTypes.gizmoCommandPlanCommand = commandName
              , GizmoTypes.gizmoCommandPlanTemplate = template
              , GizmoTypes.gizmoCommandPlanRendered = renderTemplate template args
              , GizmoTypes.gizmoCommandPlanArgs = args
              , GizmoTypes.gizmoCommandPlanCwd = "."
              , GizmoTypes.gizmoCommandPlanExecute = execute
              , GizmoTypes.gizmoCommandPlanMissingArgs = missing
              , GizmoTypes.gizmoCommandPlanUnusedArgs = unused
              }

executeCommandPlan :: GizmoTypes.GizmoCommandPlan -> IO Int
executeCommandPlan plan
  | not (GizmoTypes.gizmoCommandPlanExecute plan) = return 0
  | otherwise = do
      (_, _, _, processHandle) <-
        createProcess
          (shell (GizmoTypes.gizmoCommandPlanRendered plan))
            { cwd = Just (GizmoTypes.gizmoCommandPlanCwd plan)
            , std_in = Inherit
            , std_out = Inherit
            , std_err = Inherit
            }
      status <- waitForProcess processHandle
      return
        ( case status of
            ExitSuccess -> 0
            ExitFailure code -> code
        )

placeholders :: String -> [String]
placeholders template = Set.toAscList (Set.fromList (collectPlaceholders template))

collectPlaceholders :: String -> [String]
collectPlaceholders [] = []
collectPlaceholders ('{' : rest) =
  case parsePlaceholderName rest of
    Just (name, '}' : after) -> name : collectPlaceholders after
    _ -> collectPlaceholders rest
collectPlaceholders (_ : rest) = collectPlaceholders rest

parsePlaceholderName :: String -> Maybe (String, String)
parsePlaceholderName string =
  case string of
    c : rest
      | isAlpha c || c == '_' ->
          let (name, remainder) = span isPlaceholderChar string
           in if null name then Nothing else Just (name, remainder)
    _ -> Nothing

isPlaceholderChar c = isAlphaNum c || c == '_' || c == '-'

renderTemplate :: String -> Map.Map String String -> String
renderTemplate template args = go template
  where
    go [] = []
    go ('{' : rest) =
      case parsePlaceholderName rest of
        Just (name, '}' : after) ->
          quoteArg (Map.findWithDefault "" name args) ++ go after
        _ -> '{' : go rest
    go (c : rest) = c : go rest

quoteArg :: String -> String
quoteArg value =
  if safeArgPattern value
    then "\"" ++ value ++ "\""
    else error ("unsafe command argument: " ++ value)

safeArgPattern :: String -> Bool
safeArgPattern = all isSafeArgChar
  where
    isSafeArgChar c =
      c /= '\0'
        && c /= '\r'
        && c /= '\n'
        && c /= '"'
        && c /= '&'
        && c /= '|'
        && c /= '<'
        && c /= '>'
        && c /= '^'
        && c /= '%'

