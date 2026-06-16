module LambdaScript.Gizmo.Manifest where

import qualified Data.Aeson as Aeson
import qualified Data.Aeson.Key as Key
import qualified Data.Aeson.KeyMap as KeyMap
import qualified Data.Map.Strict as Map
import qualified Data.Set as Set
import Data.Char
import Data.Function
import Data.List
import Data.Maybe
import qualified Data.Text as Text
import System.FilePath

import qualified LambdaScript.Gizmo.Types as GizmoTypes

readManifest :: FilePath -> IO GizmoTypes.GizmoManifest
readManifest file = do
  decoded <- Aeson.decodeFileStrict' file
  case decoded of
    Just manifest -> return manifest
    Nothing -> fail ("failed to parse manifest: " ++ file)

isObject :: Aeson.Value -> Maybe Aeson.Object
isObject (Aeson.Object obj) = Just obj
isObject _ = Nothing

lookupValue :: String -> Aeson.Object -> Maybe Aeson.Value
lookupValue key obj = KeyMap.lookup (Key.fromText (Text.pack key)) obj

asString :: Aeson.Value -> Maybe Text.Text
asString (Aeson.String text) = Just text
asString _ = Nothing

asArray :: Aeson.Value -> Maybe [Aeson.Value]
asArray (Aeson.Array items) = Just (toList items)
asArray _ = Nothing

toList :: Aeson.Array -> [Aeson.Value]
toList = foldr (:) []

issue :: String -> String -> GizmoTypes.ValidationIssue
issue path message =
  GizmoTypes.ValidationIssue
    { GizmoTypes.validationIssuePath = path
    , GizmoTypes.validationIssueMessage = message
    }

isSafeName :: String -> Bool
isSafeName value =
  not (null value) && all isSafeNameChar value
  where
    isSafeNameChar c =
      isAsciiUpper c || isAsciiLower c || isDigit c || c == '.' || c == '_' || c == '-'

isSafeRef :: String -> Bool
isSafeRef value =
  not (null value)
    && not (".." `isInfixOf` value)
    && not (startsWith "/" value)
    && not (endsWith "/" value)
    && all isSafeRefChar value
  where
    isSafeRefChar c =
      isAsciiUpper c
        || isAsciiLower c
        || isDigit c
        || c == '.'
        || c == '_'
        || c == '/'
        || c == '-'

startsWith :: String -> String -> Bool
startsWith prefix value = prefix == take (length prefix) value

endsWith :: String -> String -> Bool
endsWith suffix value = suffix == drop (length value - length suffix) value

isSafeRelativePath :: String -> Bool
isSafeRelativePath value =
  let normalized = map (\c -> if c == '\\' then '/' else c) value
      parts = filter (not . null) (splitOnChar '/' normalized)
  in not (null value)
    && not ('\0' `elem` value)
    && not (':' `elem` value)
    && not (isAbsolute value)
    && all validPart parts
  where
    validPart part = not (null part) && part /= "." && part /= ".."

replaceSubstring :: String -> String -> String -> String
replaceSubstring old new string =
  case breakSubstring old string of
    (before, remainder) ->
      if null remainder
        then string
        else before ++ new ++ replaceSubstring old new (drop (length old) remainder)

breakSubstring :: String -> String -> (String, String)
breakSubstring needle haystack = go 0 haystack
  where
    go offset [] = (haystack, [])
    go offset str@(c : rest)
      | needle `isPrefixOf` str = (take offset haystack, str)
      | otherwise = go (offset + 1) rest

splitOnChar :: Char -> String -> [String]
splitOnChar sep string = go string []
  where
    go [] acc =
      case reverse acc of
        "" -> []
        part -> [part]
    go (c : rest) acc
      | c == sep =
          case reverse acc of
            "" -> go rest []
            part -> part : go rest []
      | otherwise = go rest (c : acc)

stringArrayIssues :: Aeson.Value -> String -> String -> [GizmoTypes.ValidationIssue]
stringArrayIssues value pathName itemLabel =
  case asArray value of
    Nothing -> [issue pathName (itemLabel ++ " must be an array")]
    Just items ->
      concat
        [ if isNonEmptyString item
            then []
            else [issue (pathName ++ "." ++ show index) (itemLabel ++ " entry must be a non-empty string")]
        | (index, item) <- zip [0 ..] items
        ]

optionalStringArrayIssues :: Maybe Aeson.Value -> String -> String -> [GizmoTypes.ValidationIssue]
optionalStringArrayIssues Nothing _ _ = []
optionalStringArrayIssues (Just value) pathName itemLabel =
  stringArrayIssues value pathName itemLabel

isNonEmptyString :: Aeson.Value -> Bool
isNonEmptyString value =
  case asString value of
    Just text -> not (null (dropWhile isSpace (Text.unpack text)))
    Nothing -> False

validateGadget :: String -> Aeson.Value -> [GizmoTypes.ValidationIssue]
validateGadget name rawGadget =
  let base = "gadgets." ++ name
      nameIssues =
        if isSafeName name
          then []
          else [issue base "gadget name must be filesystem-safe"]
  in case isObject rawGadget of
    Nothing -> nameIssues ++ [issue base "gadget must be an object"]
    Just gadgetObj ->
      let rootIssues =
            case lookupValue "root" gadgetObj >>= asString of
              Just root
                | isSafeRelativePath (Text.unpack root) -> []
              _ -> [issue (base ++ ".root") "root must be a safe relative path"]
          languageIssues =
            case lookupValue "language" gadgetObj of
              Nothing -> []
              Just languageValue ->
                case asString languageValue >>= GizmoTypes.gadgetLanguageFromString . Text.unpack of
                  Just _ -> []
                  _ -> [issue (base ++ ".language") "unsupported language"]
          allowedOpsIssues =
            case lookupValue "allowed_ops" gadgetObj of
              Nothing -> []
              Just opsValue ->
                case asArray opsValue of
                  Nothing -> [issue (base ++ ".allowed_ops") "allowed_ops must be an array when present"]
                  Just ops ->
                    concat
                      [ case asString op >>= GizmoTypes.gadgetOperationFromString . Text.unpack of
                          Just _ -> []
                          _ -> [issue (base ++ ".allowed_ops") ("unsupported operation " ++ show op)]
                      | op <- ops
                      ]
          commandsIssues =
            case lookupValue "commands" gadgetObj of
              Nothing -> [issue (base ++ ".commands") "commands must be an object"]
              Just commandsValue ->
                case isObject commandsValue of
                  Nothing -> [issue (base ++ ".commands") "commands must be an object"]
                  Just commandsObj ->
                    concat
                      [ let commandPath = base ++ ".commands." ++ Text.unpack (Key.toText commandKey)
                        in (if isSafeName (Text.unpack (Key.toText commandKey))
                              then []
                              else [issue commandPath "command name must be safe"])
                          ++ case asString commandValue of
                            Just command
                              | not (null (dropWhile isSpace (Text.unpack command))) -> []
                            _ -> [issue commandPath "command must be a non-empty string"]
                      | (commandKey, commandValue) <- KeyMap.toList commandsObj
                      ]
          targetRefIssues =
            case lookupValue "target_ref" gadgetObj of
              Nothing -> []
              Just refValue ->
                case asString refValue of
                  Just ref
                    | isSafeRef (Text.unpack ref) -> []
                  _ -> [issue (base ++ ".target_ref") "target_ref must be a safe git ref"]
          integrationBranchIssues =
            case lookupValue "integration_branch" gadgetObj of
              Nothing -> []
              Just branchValue ->
                case asString branchValue of
                  Just branch
                    | isSafeRef (Text.unpack branch) -> []
                  _ -> [issue (base ++ ".integration_branch") "integration_branch must be a safe git ref"]
          agentBranchTemplateIssues =
            case lookupValue "agent_branch_template" gadgetObj of
              Nothing -> []
              Just templateValue ->
                case asString templateValue of
                  Just template
                    | "{agent}" `isInfixOf` Text.unpack template
                      , isSafeRef (replaceAgent (Text.unpack template)) ->
                        []
                  _ -> [issue (base ++ ".agent_branch_template") "agent_branch_template must be a safe ref template containing {agent}"]
          ownedPathsIssues =
            optionalStringArrayIssues (lookupValue "owned_paths" gadgetObj) (base ++ ".owned_paths") "owned_paths"
            ++ case lookupValue "owned_paths" gadgetObj >>= asArray of
              Nothing -> []
              Just paths ->
                concat
                  [ case asString pathValue of
                      Just path
                        | isSafeRelativePath (dropTrailingSlash (Text.unpack path)) -> []
                      _ -> [issue (base ++ ".owned_paths." ++ show index) "owned path must be safe and relative"]
                  | (index, pathValue) <- zip [0 ..] paths
                  ]
          verificationProfilesIssues =
            case lookupValue "verification_profiles" gadgetObj of
              Nothing -> []
              Just profilesValue ->
                case isObject profilesValue of
                  Nothing -> [issue (base ++ ".verification_profiles") "verification_profiles must be an object"]
                  Just profilesObj ->
                    concat
                      [ let profilePath = base ++ ".verification_profiles." ++ Text.unpack (Key.toText profileKey)
                        in (if isSafeName (Text.unpack (Key.toText profileKey))
                              then []
                              else [issue profilePath "profile name must be safe"])
                          ++ stringArrayIssues commandsValue profilePath "verification command"
                      | (profileKey, commandsValue) <- KeyMap.toList profilesObj
                      ]
          promotionIssues =
            case lookupValue "promotion" gadgetObj of
              Nothing -> []
              Just promotionValue ->
                case isObject promotionValue of
                  Nothing -> [issue (base ++ ".promotion") "promotion must be an object"]
                  Just promotionObj ->
                    (case lookupValue "target" promotionObj of
                       Nothing -> []
                       Just targetValue ->
                         case asString targetValue of
                           Just _ -> []
                           _ -> [issue (base ++ ".promotion.target") "target must be a string"])
                      ++ (case lookupValue "verification" promotionObj of
                            Nothing -> []
                            Just verificationValue ->
                              case asString verificationValue of
                                Just _ -> []
                                _ -> [issue (base ++ ".promotion.verification") "verification must be a string"])
       in nameIssues
            ++ rootIssues
            ++ languageIssues
            ++ allowedOpsIssues
            ++ commandsIssues
            ++ targetRefIssues
            ++ integrationBranchIssues
            ++ agentBranchTemplateIssues
            ++ ownedPathsIssues
            ++ verificationProfilesIssues
            ++ promotionIssues
  where
    replaceAgent template = replaceSubstring "{agent}" "agent" template

    dropTrailingSlash path =
      if endsWith "/" path && length path > 1
        then init path
        else path

validateImport :: String -> Aeson.Value -> [GizmoTypes.ValidationIssue]
validateImport name rawImport =
  let base = "imports." ++ name
      nameIssues =
        if isSafeName name
          then []
          else [issue base "import name must be safe"]
  in case isObject rawImport of
    Nothing -> nameIssues ++ [issue base "import must be an object"]
    Just importObj ->
      let requiredFieldIssues =
            concat
              [ case lookupValue key importObj >>= asString of
                  Just text
                    | not (null (dropWhile isSpace (Text.unpack text))) -> []
                  _ -> [issue (base ++ "." ++ key) (key ++ " must be a non-empty string")]
              | key <- ["from_gizmo", "from_gadget", "mount", "mode"]
              ]
          fromGizmoIssues =
            case lookupValue "from_gizmo" importObj >>= asString of
              Just fromGizmo
                | isSafeName (Text.unpack fromGizmo) -> []
              _ -> [issue (base ++ ".from_gizmo") "from_gizmo must be safe"]
          fromGadgetIssues =
            case lookupValue "from_gadget" importObj >>= asString of
              Just fromGadget
                | isSafeName (Text.unpack fromGadget) -> []
              _ -> [issue (base ++ ".from_gadget") "from_gadget must be safe"]
          mountIssues =
            case lookupValue "mount" importObj >>= asString of
              Just mount
                | isSafeRelativePath (Text.unpack mount) -> []
              _ -> [issue (base ++ ".mount") "mount must be a safe relative path"]
          modeIssues =
            case lookupValue "mode" importObj >>= asString >>= GizmoTypes.importModeFromString . Text.unpack of
              Just _ -> []
              _ -> [issue (base ++ ".mode") "unsupported import mode"]
          targetRefIssues =
            case lookupValue "target_ref" importObj of
              Nothing -> []
              Just refValue ->
                case asString refValue of
                  Just ref
                    | isSafeRef (Text.unpack ref) -> []
                  _ -> [issue (base ++ ".target_ref") "target_ref must be a safe git ref"]
          allowedCommandsIssues =
            optionalStringArrayIssues (lookupValue "allowed_commands" importObj) (base ++ ".allowed_commands") "allowed command"
          writePolicyIssues =
            case lookupValue "write_policy" importObj of
              Nothing -> []
              Just policyValue ->
                case asString policyValue >>= GizmoTypes.writePolicyFromString . Text.unpack of
                  Just _ -> []
                  _ -> [issue (base ++ ".write_policy") "unsupported write policy"]
       in nameIssues
            ++ requiredFieldIssues
            ++ fromGizmoIssues
            ++ fromGadgetIssues
            ++ mountIssues
            ++ modeIssues
            ++ targetRefIssues
            ++ allowedCommandsIssues
            ++ writePolicyIssues

validateConnection :: Int -> Aeson.Value -> Set.Set String -> [GizmoTypes.ValidationIssue]
validateConnection index rawConnection gadgetNames =
  let base = "connections." ++ show index
  in case isObject rawConnection of
    Nothing -> [issue base "connection must be an object"]
    Just connectionObj ->
      let endpointIssues =
            concat
              [ case lookupValue key connectionObj >>= asString of
                  Just endpoint
                    | Text.unpack endpoint `Set.member` gadgetNames -> []
                  _ -> [issue (base ++ "." ++ key) (key ++ " must name a local gadget")]
              | key <- ["from", "to"]
              ]
          viaIssues =
            case lookupValue "via" connectionObj of
              Nothing -> []
              Just viaValue ->
                case asString viaValue of
                  Just _ -> []
                  _ -> [issue (base ++ ".via") "via must be a string"]
          allowedReadsIssues =
            optionalStringArrayIssues (lookupValue "allowed_reads" connectionObj) (base ++ ".allowed_reads") "allowed read"
          allowedCommandsIssues =
            optionalStringArrayIssues (lookupValue "allowed_commands" connectionObj) (base ++ ".allowed_commands") "allowed command"
       in endpointIssues ++ viaIssues ++ allowedReadsIssues ++ allowedCommandsIssues

validateManifest :: Aeson.Value -> [GizmoTypes.ValidationIssue]
validateManifest value =
  case isObject value of
    Nothing -> [issue "$" "manifest must be an object"]
    Just manifestObj ->
      let formatIssues =
            case lookupValue "format" manifestObj >>= asString of
              Just format
                | Text.unpack format == GizmoTypes.gizmoFormat -> []
              _ -> [issue "format" ("expected " ++ GizmoTypes.gizmoFormat)]
          nameIssues =
            case lookupValue "name" manifestObj >>= asString of
              Just name
                | not (null (dropWhile isSpace (Text.unpack name)))
                  , isSafeName (Text.unpack name) ->
                    []
              _ -> [issue "name" "name must be a non-empty safe string"]
       in case lookupValue "gadgets" manifestObj of
            Nothing -> formatIssues ++ nameIssues ++ [issue "gadgets" "gadgets must be an object"]
            Just gadgetsValue ->
              case isObject gadgetsValue of
                Nothing -> formatIssues ++ nameIssues ++ [issue "gadgets" "gadgets must be an object"]
                Just gadgetsObj ->
                  let gadgetNames =
                        Set.fromList [Text.unpack (Key.toText gadgetKey) | gadgetKey <- KeyMap.keys gadgetsObj]
                      gadgetValidationIssues =
                        concat
                          [ validateGadget (Text.unpack (Key.toText gadgetKey)) gadgetValue
                          | (gadgetKey, gadgetValue) <- KeyMap.toList gadgetsObj
                          ]
                      importsIssues =
                        case lookupValue "imports" manifestObj of
                          Nothing -> []
                          Just importsValue ->
                            case isObject importsValue of
                              Nothing -> [issue "imports" "imports must be an object"]
                              Just importsObj ->
                                concat
                                  [ validateImport (Text.unpack (Key.toText importKey)) importValue
                                  | (importKey, importValue) <- KeyMap.toList importsObj
                                  ]
                      connectionsIssues =
                        case lookupValue "connections" manifestObj of
                          Nothing -> []
                          Just connectionsValue ->
                            case asArray connectionsValue of
                              Nothing -> [issue "connections" "connections must be an array"]
                              Just connections ->
                                concat
                                  [ validateConnection index connectionValue gadgetNames
                                  | (index, connectionValue) <- zip [0 ..] connections
                                  ]
                   in formatIssues
                        ++ nameIssues
                        ++ gadgetValidationIssues
                        ++ importsIssues
                        ++ connectionsIssues

buildStatus :: GizmoTypes.GizmoManifest -> GizmoTypes.GizmoStatus
buildStatus manifest =
  let gadgets =
        sortBy (compare `on` GizmoTypes.gadgetStatusName)
          [ GizmoTypes.GadgetStatusEntry
              { GizmoTypes.gadgetStatusName = name
              , GizmoTypes.gadgetStatusRoot = GizmoTypes.gadgetManifestRoot gadget
              , GizmoTypes.gadgetStatusLanguage = fromMaybe GizmoTypes.GadgetUnknown (GizmoTypes.gadgetManifestLanguage gadget)
              , GizmoTypes.gadgetStatusAllowedOps = fromMaybe [] (GizmoTypes.gadgetManifestAllowedOps gadget)
              , GizmoTypes.gadgetStatusCommands = sort (Map.keys (GizmoTypes.gadgetManifestCommands gadget))
              , GizmoTypes.gadgetStatusOwnedPaths = sort (fromMaybe [] (GizmoTypes.gadgetManifestOwnedPaths gadget))
              , GizmoTypes.gadgetStatusTargetRef = GizmoTypes.gadgetManifestTargetRef gadget
              , GizmoTypes.gadgetStatusIntegrationBranch = GizmoTypes.gadgetManifestIntegrationBranch gadget
              , GizmoTypes.gadgetStatusAgentBranchTemplate = GizmoTypes.gadgetManifestAgentBranchTemplate gadget
              , GizmoTypes.gadgetStatusVerificationProfiles =
                  sort (Map.keys (fromMaybe Map.empty (GizmoTypes.gadgetManifestVerificationProfiles gadget)))
              , GizmoTypes.gadgetStatusPromotionTarget = GizmoTypes.gadgetManifestPromotion gadget >>= GizmoTypes.gadgetPromotionTarget
              , GizmoTypes.gadgetStatusPromotionVerification =
                  fromMaybe "quick" (GizmoTypes.gadgetManifestPromotion gadget >>= GizmoTypes.gadgetPromotionVerification)
              }
          | (name, gadget) <- Map.toList (GizmoTypes.gizmoManifestGadgets manifest)
          ]
      imports =
        sortBy (compare `on` GizmoTypes.importStatusName)
          [ GizmoTypes.ImportStatusEntry
              { GizmoTypes.importStatusName = name
              , GizmoTypes.importStatusFromGizmo = GizmoTypes.gizmoImportFromGizmo item
              , GizmoTypes.importStatusFromGadget = GizmoTypes.gizmoImportFromGadget item
              , GizmoTypes.importStatusMount = GizmoTypes.gizmoImportMount item
              , GizmoTypes.importStatusMode = GizmoTypes.importModeToString (GizmoTypes.gizmoImportMode item)
              , GizmoTypes.importStatusTargetRef = GizmoTypes.gizmoImportTargetRef item
              , GizmoTypes.importStatusAllowedCommands = sort (fromMaybe [] (GizmoTypes.gizmoImportAllowedCommands item))
              , GizmoTypes.importStatusWritePolicy = fmap GizmoTypes.writePolicyToString (GizmoTypes.gizmoImportWritePolicy item)
              }
          | (name, item) <- Map.toList (fromMaybe Map.empty (GizmoTypes.gizmoManifestImports manifest))
          ]
      connections = fromMaybe [] (GizmoTypes.gizmoManifestConnections manifest)
   in GizmoTypes.GizmoStatus
        { GizmoTypes.gizmoStatusFormat = GizmoTypes.gizmoFormat
        , GizmoTypes.gizmoStatusName = GizmoTypes.gizmoManifestName manifest
        , GizmoTypes.gizmoStatusDescription = GizmoTypes.gizmoManifestDescription manifest
        , GizmoTypes.gizmoStatusGadgetCount = length gadgets
        , GizmoTypes.gizmoStatusImportCount = length imports
        , GizmoTypes.gizmoStatusConnectionCount = length connections
        , GizmoTypes.gizmoStatusGadgets = gadgets
        , GizmoTypes.gizmoStatusImports = imports
        , GizmoTypes.gizmoStatusConnections = connections
        }

buildProvisionPlan :: GizmoTypes.GizmoManifest -> GizmoTypes.GizmoProvisionPlan
buildProvisionPlan manifest =
  let imports =
        sortBy (compare `on` GizmoTypes.provisionImportName)
          [ let writePolicy =
                  fromMaybe
                    (if GizmoTypes.gizmoImportMode item == GizmoTypes.ImportCopy then GizmoTypes.WriteCopyOnWrite else GizmoTypes.WriteDeny)
                    (GizmoTypes.gizmoImportWritePolicy item)
                mutable = writePolicy == GizmoTypes.WriteAllow || writePolicy == GizmoTypes.WriteCopyOnWrite
             in GizmoTypes.ProvisionImportEntry
                  { GizmoTypes.provisionImportName = name
                  , GizmoTypes.provisionImportSource = GizmoTypes.gizmoImportFromGizmo item ++ "/" ++ GizmoTypes.gizmoImportFromGadget item
                  , GizmoTypes.provisionImportMount = GizmoTypes.gizmoImportMount item
                  , GizmoTypes.provisionImportMode = GizmoTypes.gizmoImportMode item
                  , GizmoTypes.provisionImportTargetRef = GizmoTypes.gizmoImportTargetRef item
                  , GizmoTypes.provisionImportAllowedCommands = sort (fromMaybe [] (GizmoTypes.gizmoImportAllowedCommands item))
                  , GizmoTypes.provisionImportWritePolicy = writePolicy
                  , GizmoTypes.provisionImportMutable = mutable
                  }
          | (name, item) <- Map.toList (fromMaybe Map.empty (GizmoTypes.gizmoManifestImports manifest))
          ]
      commandCount = sum (map (length . GizmoTypes.provisionImportAllowedCommands) imports)
   in GizmoTypes.GizmoProvisionPlan
        { GizmoTypes.gizmoProvisionPlanFormat = GizmoTypes.gizmoProvisionPlanFormatTag
        , GizmoTypes.gizmoProvisionPlanName = GizmoTypes.gizmoManifestName manifest
        , GizmoTypes.gizmoProvisionPlanImportCount = length imports
        , GizmoTypes.gizmoProvisionPlanCommandCount = commandCount
        , GizmoTypes.gizmoProvisionPlanImports = imports
        }

ensureManifestValid :: Aeson.Value -> GizmoTypes.GizmoManifest
ensureManifestValid value =
  let issues = validateManifest value
   in case issues of
        (_ : _) ->
          error
            ( intercalate
                "\n"
                [ GizmoTypes.validationIssuePath item ++ ": " ++ GizmoTypes.validationIssueMessage item
                | item <- issues
                ]
            )
        [] ->
          case Aeson.fromJSON value of
            Aeson.Success manifest -> manifest
            Aeson.Error err -> error err