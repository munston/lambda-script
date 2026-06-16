{-# LANGUAGE DeriveGeneric #-}

module LambdaScript.Gizmo.Types where

import Data.List
import qualified Data.Aeson as Aeson
import qualified Data.Map.Strict as Map
import qualified Data.Text as Text
import GHC.Generics

gizmoFormat :: String
gizmoFormat = "LS_GIZMO_V1"

gizmoProvisionPlanFormatTag :: String
gizmoProvisionPlanFormatTag = "LS_GIZMO_PROVISION_PLAN_V1"

gizmoCommandPlanFormatTag :: String
gizmoCommandPlanFormatTag = "LS_GIZMO_COMMAND_PLAN_V1"

data GadgetLanguage
  = GadgetPython
  | GadgetTypeScript
  | GadgetLambdaScript
  | GadgetCpp
  | GadgetMixed
  | GadgetUnknown
  deriving (Eq, Ord, Show, Read, Generic)

data GadgetOperation
  = GadgetOpRead
  | GadgetOpWrite
  | GadgetOpMkdir
  | GadgetOpCopy
  | GadgetOpRun
  deriving (Eq, Ord, Show, Read, Generic)

data ImportMode
  = ImportReadOnly
  | ImportPinned
  | ImportCopy
  deriving (Eq, Ord, Show, Read, Generic)

data WritePolicy
  = WriteDeny
  | WriteCopyOnWrite
  | WriteAllow
  deriving (Eq, Ord, Show, Read, Generic)

data GadgetPromotion = GadgetPromotion
  { gadgetPromotionTarget :: Maybe String
  , gadgetPromotionVerification :: Maybe String
  } deriving (Eq, Show, Read, Generic)

data GadgetManifest = GadgetManifest
  { gadgetManifestRoot :: String
  , gadgetManifestLanguage :: Maybe GadgetLanguage
  , gadgetManifestAllowedOps :: Maybe [GadgetOperation]
  , gadgetManifestCommands :: Map.Map String String
  , gadgetManifestDescription :: Maybe String
  , gadgetManifestTargetRef :: Maybe String
  , gadgetManifestIntegrationBranch :: Maybe String
  , gadgetManifestAgentBranchTemplate :: Maybe String
  , gadgetManifestOwnedPaths :: Maybe [String]
  , gadgetManifestVerificationProfiles :: Maybe (Map.Map String [String])
  , gadgetManifestPromotion :: Maybe GadgetPromotion
  } deriving (Eq, Show, Read, Generic)

data GizmoImportManifest = GizmoImportManifest
  { gizmoImportFromGizmo :: String
  , gizmoImportFromGadget :: String
  , gizmoImportMount :: String
  , gizmoImportMode :: ImportMode
  , gizmoImportTargetRef :: Maybe String
  , gizmoImportAllowedCommands :: Maybe [String]
  , gizmoImportWritePolicy :: Maybe WritePolicy
  } deriving (Eq, Show, Read, Generic)

data GizmoConnectionManifest = GizmoConnectionManifest
  { gizmoConnectionFrom :: String
  , gizmoConnectionTo :: String
  , gizmoConnectionVia :: Maybe String
  , gizmoConnectionAllowedReads :: Maybe [String]
  , gizmoConnectionAllowedCommands :: Maybe [String]
  } deriving (Eq, Show, Read, Generic)

data GizmoManifest = GizmoManifest
  { gizmoManifestFormat :: String
  , gizmoManifestName :: String
  , gizmoManifestDescription :: Maybe String
  , gizmoManifestGadgets :: Map.Map String GadgetManifest
  , gizmoManifestImports :: Maybe (Map.Map String GizmoImportManifest)
  , gizmoManifestConnections :: Maybe [GizmoConnectionManifest]
  } deriving (Eq, Show, Read, Generic)

data ValidationIssue = ValidationIssue
  { validationIssuePath :: String
  , validationIssueMessage :: String
  } deriving (Eq, Show, Read, Generic)

data GadgetStatusEntry = GadgetStatusEntry
  { gadgetStatusName :: String
  , gadgetStatusRoot :: String
  , gadgetStatusLanguage :: GadgetLanguage
  , gadgetStatusAllowedOps :: [GadgetOperation]
  , gadgetStatusCommands :: [String]
  , gadgetStatusOwnedPaths :: [String]
  , gadgetStatusTargetRef :: Maybe String
  , gadgetStatusIntegrationBranch :: Maybe String
  , gadgetStatusAgentBranchTemplate :: Maybe String
  , gadgetStatusVerificationProfiles :: [String]
  , gadgetStatusPromotionTarget :: Maybe String
  , gadgetStatusPromotionVerification :: String
  } deriving (Eq, Show, Read, Generic)

data ImportStatusEntry = ImportStatusEntry
  { importStatusName :: String
  , importStatusFromGizmo :: String
  , importStatusFromGadget :: String
  , importStatusMount :: String
  , importStatusMode :: String
  , importStatusTargetRef :: Maybe String
  , importStatusAllowedCommands :: [String]
  , importStatusWritePolicy :: Maybe String
  } deriving (Eq, Show, Read, Generic)

data GizmoStatus = GizmoStatus
  { gizmoStatusFormat :: String
  , gizmoStatusName :: String
  , gizmoStatusDescription :: Maybe String
  , gizmoStatusGadgetCount :: Int
  , gizmoStatusImportCount :: Int
  , gizmoStatusConnectionCount :: Int
  , gizmoStatusGadgets :: [GadgetStatusEntry]
  , gizmoStatusImports :: [ImportStatusEntry]
  , gizmoStatusConnections :: [GizmoConnectionManifest]
  } deriving (Eq, Show, Read, Generic)

data ProvisionImportEntry = ProvisionImportEntry
  { provisionImportName :: String
  , provisionImportSource :: String
  , provisionImportMount :: String
  , provisionImportMode :: ImportMode
  , provisionImportTargetRef :: Maybe String
  , provisionImportAllowedCommands :: [String]
  , provisionImportWritePolicy :: WritePolicy
  , provisionImportMutable :: Bool
  } deriving (Eq, Show, Read, Generic)

data GizmoProvisionPlan = GizmoProvisionPlan
  { gizmoProvisionPlanFormat :: String
  , gizmoProvisionPlanName :: String
  , gizmoProvisionPlanImportCount :: Int
  , gizmoProvisionPlanCommandCount :: Int
  , gizmoProvisionPlanImports :: [ProvisionImportEntry]
  } deriving (Eq, Show, Read, Generic)

data GizmoCommandPlan = GizmoCommandPlan
  { gizmoCommandPlanFormat :: String
  , gizmoCommandPlanGizmo :: String
  , gizmoCommandPlanScope :: String
  , gizmoCommandPlanName :: String
  , gizmoCommandPlanCommand :: String
  , gizmoCommandPlanTemplate :: String
  , gizmoCommandPlanRendered :: String
  , gizmoCommandPlanArgs :: Map.Map String String
  , gizmoCommandPlanCwd :: String
  , gizmoCommandPlanExecute :: Bool
  , gizmoCommandPlanMissingArgs :: [String]
  , gizmoCommandPlanUnusedArgs :: [String]
  } deriving (Eq, Show, Read, Generic)

gadgetLanguageToString :: GadgetLanguage -> String
gadgetLanguageToString lang = case lang of
  GadgetPython -> "python"
  GadgetTypeScript -> "typescript"
  GadgetLambdaScript -> "lambdascript"
  GadgetCpp -> "cpp"
  GadgetMixed -> "mixed"
  GadgetUnknown -> "unknown"

gadgetLanguageFromString :: String -> Maybe GadgetLanguage
gadgetLanguageFromString text = case text of
  "python" -> Just GadgetPython
  "typescript" -> Just GadgetTypeScript
  "lambdascript" -> Just GadgetLambdaScript
  "cpp" -> Just GadgetCpp
  "mixed" -> Just GadgetMixed
  "unknown" -> Just GadgetUnknown
  _ -> Nothing

gadgetOperationToString :: GadgetOperation -> String
gadgetOperationToString op = case op of
  GadgetOpRead -> "read"
  GadgetOpWrite -> "write"
  GadgetOpMkdir -> "mkdir"
  GadgetOpCopy -> "copy"
  GadgetOpRun -> "run"

gadgetOperationFromString :: String -> Maybe GadgetOperation
gadgetOperationFromString text = case text of
  "read" -> Just GadgetOpRead
  "write" -> Just GadgetOpWrite
  "mkdir" -> Just GadgetOpMkdir
  "copy" -> Just GadgetOpCopy
  "run" -> Just GadgetOpRun
  _ -> Nothing

importModeToString :: ImportMode -> String
importModeToString mode = case mode of
  ImportReadOnly -> "read-only"
  ImportPinned -> "pinned"
  ImportCopy -> "copy"

importModeFromString :: String -> Maybe ImportMode
importModeFromString text = case text of
  "read-only" -> Just ImportReadOnly
  "pinned" -> Just ImportPinned
  "copy" -> Just ImportCopy
  _ -> Nothing

writePolicyToString :: WritePolicy -> String
writePolicyToString policy = case policy of
  WriteDeny -> "deny"
  WriteCopyOnWrite -> "copy-on-write"
  WriteAllow -> "allow"

writePolicyFromString :: String -> Maybe WritePolicy
writePolicyFromString text = case text of
  "deny" -> Just WriteDeny
  "copy-on-write" -> Just WriteCopyOnWrite
  "allow" -> Just WriteAllow
  _ -> Nothing

jsonOptions :: String -> Aeson.Options
jsonOptions prefix =
  Aeson.defaultOptions
    { Aeson.fieldLabelModifier = Aeson.camelTo2 '_' . dropPrefix prefix
    , Aeson.omitNothingFields = True
    }

dropPrefix :: String -> String -> String
dropPrefix prefix field
  | prefix `isPrefixOf` field = drop (length prefix) field
  | otherwise = field

instance Aeson.FromJSON GadgetLanguage where
  parseJSON value =
    case value of
      Aeson.String text ->
        case gadgetLanguageFromString (Text.unpack text) of
          Just language -> pure language
          Nothing -> fail "unsupported language"
      _ -> fail "language must be a string"

instance Aeson.ToJSON GadgetLanguage where
  toJSON = Aeson.String . Text.pack . gadgetLanguageToString

instance Aeson.FromJSON GadgetOperation where
  parseJSON value =
    case value of
      Aeson.String text ->
        case gadgetOperationFromString (Text.unpack text) of
          Just op -> pure op
          Nothing -> fail "unsupported operation"
      _ -> fail "operation must be a string"

instance Aeson.ToJSON GadgetOperation where
  toJSON = Aeson.String . Text.pack . gadgetOperationToString

instance Aeson.FromJSON ImportMode where
  parseJSON value =
    case value of
      Aeson.String text ->
        case importModeFromString (Text.unpack text) of
          Just mode -> pure mode
          Nothing -> fail "unsupported import mode"
      _ -> fail "import mode must be a string"

instance Aeson.ToJSON ImportMode where
  toJSON = Aeson.String . Text.pack . importModeToString

instance Aeson.FromJSON WritePolicy where
  parseJSON value =
    case value of
      Aeson.String text ->
        case writePolicyFromString (Text.unpack text) of
          Just policy -> pure policy
          Nothing -> fail "unsupported write policy"
      _ -> fail "write policy must be a string"

instance Aeson.ToJSON WritePolicy where
  toJSON = Aeson.String . Text.pack . writePolicyToString

instance Aeson.FromJSON GadgetPromotion where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gadgetPromotion")

instance Aeson.ToJSON GadgetPromotion where
  toJSON = Aeson.genericToJSON (jsonOptions "gadgetPromotion")

instance Aeson.FromJSON GadgetManifest where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gadgetManifest")

instance Aeson.ToJSON GadgetManifest where
  toJSON = Aeson.genericToJSON (jsonOptions "gadgetManifest")

instance Aeson.FromJSON GizmoImportManifest where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoImport")

instance Aeson.ToJSON GizmoImportManifest where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoImport")

instance Aeson.FromJSON GizmoConnectionManifest where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoConnection")

instance Aeson.ToJSON GizmoConnectionManifest where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoConnection")

instance Aeson.FromJSON GizmoManifest where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoManifest")

instance Aeson.ToJSON GizmoManifest where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoManifest")

instance Aeson.FromJSON ValidationIssue where
  parseJSON = Aeson.genericParseJSON (jsonOptions "validationIssue")

instance Aeson.ToJSON ValidationIssue where
  toJSON = Aeson.genericToJSON (jsonOptions "validationIssue")

instance Aeson.FromJSON GadgetStatusEntry where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gadgetStatus")

instance Aeson.ToJSON GadgetStatusEntry where
  toJSON = Aeson.genericToJSON (jsonOptions "gadgetStatus")

instance Aeson.FromJSON ImportStatusEntry where
  parseJSON = Aeson.genericParseJSON (jsonOptions "importStatus")

instance Aeson.ToJSON ImportStatusEntry where
  toJSON = Aeson.genericToJSON (jsonOptions "importStatus")

instance Aeson.FromJSON GizmoStatus where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoStatus")

instance Aeson.ToJSON GizmoStatus where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoStatus")

instance Aeson.FromJSON ProvisionImportEntry where
  parseJSON = Aeson.genericParseJSON (jsonOptions "provisionImport")

instance Aeson.ToJSON ProvisionImportEntry where
  toJSON = Aeson.genericToJSON (jsonOptions "provisionImport")

instance Aeson.FromJSON GizmoProvisionPlan where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoProvisionPlan")

instance Aeson.ToJSON GizmoProvisionPlan where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoProvisionPlan")

instance Aeson.FromJSON GizmoCommandPlan where
  parseJSON = Aeson.genericParseJSON (jsonOptions "gizmoCommandPlan")

instance Aeson.ToJSON GizmoCommandPlan where
  toJSON = Aeson.genericToJSON (jsonOptions "gizmoCommandPlan")