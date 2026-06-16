module Main where

import Audio.Features
import Data.Char (isSpace)
import Data.List (foldl', intercalate, sortOn)
import Data.WAVE
import Learn.Model
import System.Directory (doesFileExist)
import System.Environment (getArgs)
import System.Exit (die)
import System.FilePath ((</>), isRelative, takeDirectory)
import Text.Read (readMaybe)

main :: IO ()
main = do
  args <- getArgs
  case args of
    ["info", input] -> printInfo input
    ["features", input] -> printFeatures input
    ["gain", factorText, input, output] -> do
      factor <- parseDoubleIO "gain factor" factorText
      process output input (mapSamples (scaleSample factor))
    ["normalize", input, output] -> do
      wav <- getWAVEFile input
      putWAVEFile output (normalizeWAVE wav)
    ["reverse", input, output] -> process output input reverseSamples
    ["mono", input, output] -> do
      wav <- getWAVEFile input
      putWAVEFile output (toMono wav)
    ["train-centroid", dataset, modelPath] -> trainCentroidCommand dataset modelPath
    ["predict", modelPath, input] -> predictCommand modelPath input
    ["eval", modelPath, dataset] -> evalCommand modelPath dataset
    _ -> die usage

usage :: String
usage = unlines
  [ "usage:"
  , "  wavproc info <input.wav>"
  , "  wavproc features <input.wav>"
  , "  wavproc gain <factor> <input.wav> <output.wav>"
  , "  wavproc normalize <input.wav> <output.wav>"
  , "  wavproc reverse <input.wav> <output.wav>"
  , "  wavproc mono <input.wav> <output.wav>"
  , "  wavproc train-centroid <dataset.csv> <model.txt>"
  , "  wavproc predict <model.txt> <input.wav>"
  , "  wavproc eval <model.txt> <dataset.csv>"
  , ""
  , "dataset.csv format: label,path/to/file.wav"
  , "labels must not contain whitespace; relative paths are resolved from the dataset file directory."
  ]

parseDoubleIO :: String -> String -> IO Double
parseDoubleIO label text =
  case readMaybe text of
    Just x -> pure x
    Nothing -> die ("could not parse " ++ label ++ ": " ++ text)

process :: FilePath -> FilePath -> (WAVE -> WAVE) -> IO ()
process output input f = do
  wav <- getWAVEFile input
  putWAVEFile output (f wav)

printInfo :: FilePath -> IO ()
printInfo input = do
  wav <- getWAVEFile input
  let hd = waveHeader wav
      st = stats wav
  putStrLn ("channels: " ++ show (waveNumChannels hd))
  putStrLn ("frame-rate: " ++ show (waveFrameRate hd))
  putStrLn ("bits-per-sample: " ++ show (waveBitsPerSample hd))
  putStrLn ("frames: " ++ maybe (show (stFrames st)) show (waveFrames hd))
  putStrLn ("duration-seconds: " ++ showDuration hd st)
  putStrLn ("peak: " ++ show (stPeak st))
  putStrLn ("rms: " ++ show (stRms st))

printFeatures :: FilePath -> IO ()
printFeatures input = getWAVEFile input >>= putStrLn . featureLine

trainCentroidCommand :: FilePath -> FilePath -> IO ()
trainCentroidCommand dataset modelPath = do
  rows <- readDataset dataset
  training <- mapM rowFeatures rows
  case trainCentroid featureNames training of
    Left err -> die err
    Right model -> do
      writeFile modelPath (renderModel model)
      putStrLn ("trained-centroid-model: " ++ modelPath)
      putStrLn ("training-items: " ++ show (length training))
      putStrLn ("classes: " ++ intercalate ", " [lab ++ "(" ++ show count ++ ")" | (lab, count, _) <- modelClasses model])

predictCommand :: FilePath -> FilePath -> IO ()
predictCommand modelPath input = do
  model <- loadModel modelPath
  xs <- wavFeatures input
  case predictCentroid model xs of
    Left err -> die err
    Right (lab, scored) -> do
      putStrLn ("label: " ++ lab)
      putStrLn "distances:"
      mapM_ (\(l,d) -> putStrLn ("  " ++ l ++ " " ++ show d)) (sortOn snd scored)

evalCommand :: FilePath -> FilePath -> IO ()
evalCommand modelPath dataset = do
  model <- loadModel modelPath
  rows <- readDataset dataset
  results <- mapM (evalRow model) rows
  let total = length results
      correct = length [() | (expected, predicted, _) <- results, expected == predicted]
  mapM_ printEval results
  putStrLn ("total: " ++ show total)
  putStrLn ("correct: " ++ show correct)
  putStrLn ("accuracy: " ++ showAccuracy correct total)

rowFeatures :: (String, FilePath) -> IO (String, [Double])
rowFeatures (lab,path) = do
  xs <- wavFeatures path
  pure (lab,xs)

wavFeatures :: FilePath -> IO [Double]
wavFeatures path = extractFeatures <$> getWAVEFile path

loadModel :: FilePath -> IO CentroidModel
loadModel path = do
  text <- readFile path
  case parseModel text of
    Left err -> die err
    Right model -> pure model

evalRow :: CentroidModel -> (String, FilePath) -> IO (String, String, FilePath)
evalRow model (expected,path) = do
  xs <- wavFeatures path
  case predictCentroid model xs of
    Left err -> die err
    Right (predicted, _) -> pure (expected, predicted, path)

printEval :: (String, String, FilePath) -> IO ()
printEval (expected, predicted, path) =
  putStrLn (status ++ " expected=" ++ expected ++ " predicted=" ++ predicted ++ " file=" ++ path)
  where
    status = if expected == predicted then "ok" else "miss"

showAccuracy :: Int -> Int -> String
showAccuracy _ 0 = "0"
showAccuracy correct total = show (fromIntegral correct / fromIntegral total :: Double)

readDataset :: FilePath -> IO [(String, FilePath)]
readDataset dataset = do
  text <- readFile dataset
  let base = takeDirectory dataset
      numbered = zip [(1 :: Int)..] (lines text)
  fmap concat (mapM (parseDatasetLine base) numbered)

parseDatasetLine :: FilePath -> (Int, String) -> IO [(String, FilePath)]
parseDatasetLine base (lineNo, raw)
  | null trimmed = pure []
  | "#" `prefixOf` trimmed = pure []
  | otherwise =
      case break (== ',') trimmed of
        (lab, ',':rest)
          | null (trim lab) -> die ("dataset line " ++ show lineNo ++ ": empty label")
          | any isSpace (trim lab) -> die ("dataset line " ++ show lineNo ++ ": label contains whitespace")
          | otherwise -> do
              let path = resolveRelative base (trim rest)
              exists <- doesFileExist path
              if exists then pure [(trim lab, path)] else die ("dataset line " ++ show lineNo ++ ": missing file " ++ path)
        _ -> die ("dataset line " ++ show lineNo ++ ": expected label,path")
  where
    trimmed = trim raw

resolveRelative :: FilePath -> FilePath -> FilePath
resolveRelative base path
  | isRelative path = base </> path
  | otherwise = path

prefixOf :: String -> String -> Bool
prefixOf needle haystack = take (length needle) haystack == needle

trim :: String -> String
trim = dropWhileEnd isSpace . dropWhile isSpace

dropWhileEnd :: (a -> Bool) -> [a] -> [a]
dropWhileEnd p = reverse . dropWhile p . reverse

data Stats = Stats
  { stFrames :: !Int
  , stPeak :: !Double
  , stRms :: !Double
  }

showDuration :: WAVEHeader -> Stats -> String
showDuration hd st = show (fromIntegral (stFrames st) / fromIntegral (waveFrameRate hd) :: Double)

stats :: WAVE -> Stats
stats (WAVE _ frames) =
  let flattened = concat frames
      count = length flattened
      peak = foldl' max 0 (map (abs . sampleToDouble) flattened)
      squares = foldl' (\a s -> let x = sampleToDouble s in a + x * x) 0 flattened
      rms = if count == 0 then 0 else sqrt (squares / fromIntegral count)
  in Stats (length frames) peak rms

mapSamples :: (WAVESample -> WAVESample) -> WAVE -> WAVE
mapSamples f wav = wav { waveSamples = map (map f) (waveSamples wav) }

scaleSample :: Double -> WAVESample -> WAVESample
scaleSample factor = doubleToSample . clampUnit . (* factor) . sampleToDouble

normalizeWAVE :: WAVE -> WAVE
normalizeWAVE wav =
  let peak = stPeak (stats wav)
  in if peak <= 0 then wav else mapSamples (scaleSample (1 / peak)) wav

reverseSamples :: WAVE -> WAVE
reverseSamples wav = wav { waveSamples = reverse (waveSamples wav) }

toMono :: WAVE -> WAVE
toMono (WAVE hd frames) = WAVE (hd { waveNumChannels = 1 }) (map averageFrame frames)

averageFrame :: [WAVESample] -> [WAVESample]
averageFrame [] = [0]
averageFrame xs = [doubleToSample (sum (map sampleToDouble xs) / fromIntegral (length xs))]

clampUnit :: Double -> Double
clampUnit x
  | x > 1 = 1
  | x < -1 = -1
  | otherwise = x
