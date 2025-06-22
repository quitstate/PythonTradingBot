import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class BacktestIsolationForestAnomalyDetector:
    """
    Anomaly detector using the Isolation Forest algorithm.
    Analyzes windows of multivariate time series data to identify
    unusual behavior patterns.
    """
    def __init__(
        self,
        window_size=1,  # Número de pasos temporales en cada ventana
        n_estimators=100,
        contamination='auto',
        max_samples='auto',
        random_state=None,  # Number of time steps in each window
        features=None  # List of column names to use as features
    ):
        self.window_size = window_size
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            bootstrap=False  # bootstrap=False is default in newer versions and often recommended
        )
        self.trained = False  # Stores the decision scores of the training data
        self.decision_scores_train = []
        self.features = features if features else ['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']
        self.num_features_per_timestep = len(self.features)
        self.threshold = None  # Threshold for anomaly detection

    def _create_windows(self, data_df: pd.DataFrame):
        """
        Creates sliding windows from a time series DataFrame.
        Each window is flattened to be a single sample for Isolation Forest.
        """
        if not isinstance(data_df, pd.DataFrame):  # data_df must be a pandas DataFrame.
            raise ValueError("data_df must be a pandas DataFrame.")
        if data_df.empty or len(data_df) < self.window_size:
            return np.array([])

        # Ensure that only the columns specified in self.features are used
        data_for_windows = data_df[self.features].values

        windows = []
        for i in range(len(data_for_windows) - self.window_size + 1):
            window = data_for_windows[i:i + self.window_size, :]  # Flatten the window
            windows.append(window.flatten())
        return np.array(windows).astype(np.float32) if windows else np.array([])

    def fit(self, data_df: pd.DataFrame):
        """
        Trains the Isolation Forest model with the provided time series DataFrame.
        The data_df is converted into sliding windows.
        """
        if len(data_df) < self.window_size:
            raise ValueError(
                f"La longitud de la serie de datos ({len(data_df)}) debe ser al menos "
                f"igual al tamaño de la ventana ({self.window_size})."
            )

        windows = self._create_windows(data_df)
        if windows.shape[0] == 0:  # Not enough data to create training windows.
            raise ValueError("Not enough data to create training windows.")

        self.model.fit(windows)

        # Store the decision scores of the training data to set a threshold
        # Lower scores are more anomalous. We use the negative so that higher scores
        # are more anomalous.
        self.decision_scores_train = -self.model.decision_function(windows)

        self.trained = True
        print("Isolation Forest model training completed.")

    def get_anomaly_score_for_window(self, window_data_df_slice: pd.DataFrame):
        """
        Calcula el score de anomalía para una única ventana de datos.
        window_data_df_slice: un slice del DataFrame original que representa una ventana.
        """
        if not self.trained:
            raise RuntimeError("The model has not been trained. Call fit() first.")
        if len(window_data_df_slice) != self.window_size:
            raise ValueError(
                f"The length of window_data_df_slice ({len(window_data_df_slice)}) must match "
                f"the model's window_size ({self.window_size})."
            )

        # Ensure that only the columns specified in self.features are used
        window_features = window_data_df_slice[self.features].values.flatten().astype(np.float32)
        window_reshaped = window_features.reshape(1, -1)  # IsolationForest expects a 2D array

        # We use the negative of decision_function so that higher scores indicate greater anomaly
        score = -self.model.decision_function(window_reshaped)[0]
        return score  # Determines if a data window is anomalous based on a threshold.

    def is_window_anomalous(self, window_data_df_slice: pd.DataFrame, threshold: float):
        """Determina si una ventana de datos es anómala basándose en un umbral."""
        if self.threshold is None and threshold is None:
            raise ValueError(
                "El umbral no ha sido establecido. "
                "Llama a set_threshold_from_train_data() o provee un umbral."
            )  # The threshold has not been set. Call set_threshold_from_train_data() or provide a threshold.
        current_threshold = threshold if threshold is not None else self.threshold
        score = self.get_anomaly_score_for_window(window_data_df_slice)
        return score > current_threshold

    def detect_anomalies_in_series(self, data_df: pd.DataFrame, threshold: float = None):
        """
        Detects anomalies in a new data series by processing it in windows.
        Returns a list of tuples: (window_index, window_data, score, is_anomaly)
        """
        if not self.trained:
            raise RuntimeError("The model has not been trained. Call fit() first.")

        current_threshold = threshold if threshold is not None else self.threshold
        if current_threshold is None:
            raise ValueError("El umbral no ha sido establecido ni provisto.")

        if len(data_df) < self.window_size:
            print("No hay suficientes datos en la serie para formar ventanas.")
            return []  # Not enough data in the series to form windows.

        anomalies_detected = []
        for i in range(len(data_df) - self.window_size + 1):
            window_slice_df = data_df.iloc[i:i + self.window_size]
            score = self.get_anomaly_score_for_window(window_slice_df)
            is_anom = score > current_threshold
            anomalies_detected.append(
                (i, window_slice_df[self.features].values.tolist(), score, is_anom)
            )
        return anomalies_detected

    def set_threshold_from_train_data(self, percentile=95):
        """
        Sets an anomaly threshold based on the decision scores of the training data.
        A higher score (after negating decision_function) indicates greater anomaly.
        """
        if not self.trained or len(self.decision_scores_train) == 0:
            raise RuntimeError(
                "Model not trained or no training decision scores available. "
                "Call fit() first."
            )
        self.threshold = np.percentile(self.decision_scores_train, percentile)
        print(
            f"Anomaly threshold set to: {self.threshold:.5f} "
            f"(based on the {percentile} percentile of training decision scores)"
        )
        return self.threshold  # Example usage:


# Ejemplo de uso:
if __name__ == "__main__":
    # Simula datos de series temporales con las columnas especificadas
    data = {
        'open': np.random.rand(100) * 10 + 100,
        'high': np.random.rand(100) * 10 + 105,
        'low': np.random.rand(100) * 10 + 95,
        'close': np.random.rand(100) * 10 + 100,
        'tickvol': np.random.randint(100, 1000, 100),
        'vol': np.random.randint(1000, 10000, 100),
        'spread': np.random.randint(1, 5, 100)
    }
    # Add some simulated anomalies
    data['close'][20:23] = data['close'][20:23] * 1.2  # Anomalous increase
    data['tickvol'][50:53] = data['tickvol'][50:53] * 5  # Anomalous volume
    data['low'][70:73] = data['low'][70:73] * 0.8  # Anomalous drop

    data_df = pd.DataFrame(data)
    # Ensure 'high' is always >= 'open' and 'close', and 'low' <= 'open' and 'close'
    data_df['high'] = data_df[['open', 'close', 'high']].max(axis=1)
    data_df['low'] = data_df[['open', 'close', 'low']].min(axis=1)

    window_s = 5  # Analyze windows of 5 time steps

    # List of features to use by the detector
    features_to_use = ['open', 'high', 'low', 'close', 'tickvol']

    detector = BacktestIsolationForestAnomalyDetector(
        window_size=window_s,
        features=features_to_use,
        random_state=42
    )  # Train the model

    # For a real scenario, use a period of "normal" data for training
    print(f"Training Isolation Forest with window_size={window_s}...")
    # Use a portion of the data for training, simulating normal data
    train_data_df = data_df.iloc[:80]  # Use the first 80 points for training
    detector.fit(train_data_df)

    # Establecer el umbral basado en los scores de decisión de los datos de entrenamiento
    threshold = detector.set_threshold_from_train_data(
        percentile=95
    )  # Umbral más alto para detectar anomalías más evidentes

    print(
        f"\nDetectando anomalías en la serie completa usando "
        f"window_size={window_s} y umbral={threshold:.5f}:"
    )
    # Detectar anomalías en la serie completa
    anomalies_info = detector.detect_anomalies_in_series(data_df, threshold)
    # Detecting anomalies in the full series using
    if not anomalies_info:  # No windows were created for analysis or no anomalies were detected.
        print("No windows were created for analysis or no anomalies were detected.")
    else:
        for i, window, score, is_anom in anomalies_info:
            # window is a list of lists (window_size x num_features)
            # To print, we can show a summary or the first features of the first row
            # of the window
            first_step_features = ", ".join([f"{val:.2f}" for val in window[0]])
            print(
                f"Ventana desde índice {i} (primer paso: [{first_step_features}, ...]): "
                f"Score={score:.5f} {'<- ANOMALÍA DETECTADA' if is_anom else ''}"
            )
