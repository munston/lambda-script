module Learn.Model
  ( CentroidModel(..)
  , trainCentroid
  , predictCentroid
  , renderModel
  , parseModel
  ) where

import Data.List (groupBy, intercalate, minimumBy, sortOn, transpose)
import Data.Ord (comparing)
import Text.Read (readMaybe)

data CentroidModel = CentroidModel
  { modelFeatureNames :: [String]
  , modelMeans :: [Double]
  , modelScales :: [Double]
  , modelClasses :: [(String, Int, [Double])]
  } deriving (Eq, Show)

trainCentroid :: [String] -> [(String, [Double])] -> Either String CentroidModel
trainCentroid names rows
  | null rows = Left "empty training set"
  | any ((/= width) . length . snd) rows = Left "inconsistent feature vector width"
  | width /= length names = Left "feature name count does not match feature vector width"
  | otherwise = Right (CentroidModel names means scales classes)
  where
    width = length (snd (head rows))
    vectors = map snd rows
    columns = transpose vectors
    means = map mean columns
    scales = map std columns
    normRows = [(lab, standardize means scales xs) | (lab,xs) <- rows]
    grouped = groupBy (\a b -> fst a == fst b) (sortOn fst normRows)
    classes = map classCentroid grouped

classCentroid :: [(String, [Double])] -> (String, Int, [Double])
classCentroid rows =
  let lab = fst (head rows)
      vectors = map snd rows
      count = length vectors
      centre = map mean (transpose vectors)
  in (lab, count, centre)

predictCentroid :: CentroidModel -> [Double] -> Either String (String, [(String, Double)])
predictCentroid model xs
  | length xs /= length (modelMeans model) = Left "feature vector width does not match model"
  | null (modelClasses model) = Left "model has no classes"
  | otherwise = Right (best, scored)
  where
    nx = standardize (modelMeans model) (modelScales model) xs
    scored = [(lab, squaredDistance nx centre) | (lab, _, centre) <- modelClasses model]
    best = fst (minimumBy (comparing snd) scored)

renderModel :: CentroidModel -> String
renderModel model = unlines $
  [ "WAVPROC-CENTROID 1"
  , "FEATURES " ++ show (length (modelFeatureNames model))
  , "NAMES " ++ unwords (modelFeatureNames model)
  , "MEAN " ++ renderDoubles (modelMeans model)
  , "SCALE " ++ renderDoubles (modelScales model)
  ] ++ map renderClass (modelClasses model)

parseModel :: String -> Either String CentroidModel
parseModel text =
  case lines text of
    (magic:featureLine':namesLine:meanLine:scaleLine:classLines)
      | magic /= "WAVPROC-CENTROID 1" -> Left "bad model header"
      | otherwise -> do
          width <- parseFeatures featureLine'
          names <- parseNames namesLine
          means <- parseDoublesLine "MEAN" meanLine
          scales <- parseDoublesLine "SCALE" scaleLine
          classes <- mapM parseClass classLines
          ensure "feature count mismatch" (length names == width)
          ensure "mean vector width mismatch" (length means == width)
          ensure "scale vector width mismatch" (length scales == width)
          ensure "class centroid width mismatch" (all (\(_,_,xs) -> length xs == width) classes)
          pure (CentroidModel names means scales classes)
    _ -> Left "incomplete model file"

parseFeatures :: String -> Either String Int
parseFeatures lineText =
  case words lineText of
    ["FEATURES", nText] -> maybe (Left "bad feature count") Right (readMaybe nText)
    _ -> Left "bad FEATURES line"

parseNames :: String -> Either String [String]
parseNames lineText =
  case words lineText of
    ("NAMES":names) -> Right names
    _ -> Left "bad NAMES line"

parseDoublesLine :: String -> String -> Either String [Double]
parseDoublesLine key lineText =
  case words lineText of
    (k:xs) | k == key -> mapM parseDouble xs
    _ -> Left ("bad " ++ key ++ " line")

parseClass :: String -> Either String (String, Int, [Double])
parseClass lineText =
  case words lineText of
    ("CLASS":lab:countText:xs) -> do
      count <- maybe (Left "bad class count") Right (readMaybe countText)
      centre <- mapM parseDouble xs
      Right (lab, count, centre)
    _ -> Left "bad CLASS line"

parseDouble :: String -> Either String Double
parseDouble x = maybe (Left ("bad floating point value: " ++ x)) Right (readMaybe x)

ensure :: String -> Bool -> Either String ()
ensure msg ok = if ok then Right () else Left msg

renderClass :: (String, Int, [Double]) -> String
renderClass (lab, count, centre) = "CLASS " ++ lab ++ " " ++ show count ++ " " ++ renderDoubles centre

renderDoubles :: [Double] -> String
renderDoubles = intercalate " " . map show

standardize :: [Double] -> [Double] -> [Double] -> [Double]
standardize means scales xs = zipWith3 (\m s x -> (x - m) / safeScale s) means scales xs

safeScale :: Double -> Double
safeScale s
  | abs s <= 1.0e-12 = 1
  | otherwise = s

mean :: [Double] -> Double
mean [] = 0
mean xs = sum xs / fromIntegral (length xs)

std :: [Double] -> Double
std [] = 1
std xs =
  let m = mean xs
      v = sum [(x - m) * (x - m) | x <- xs] / fromIntegral (length xs)
      s = sqrt v
  in if s <= 1.0e-12 then 1 else s

squaredDistance :: [Double] -> [Double] -> Double
squaredDistance xs ys = sum (zipWith (\a b -> let d = a - b in d * d) xs ys)
