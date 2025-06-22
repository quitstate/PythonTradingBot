import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class IsolationForestAnomalyDetector:
    """
    Detector de anomalías utilizando el algoritmo Isolation Forest.
    Analiza ventanas de datos de series temporales multivariadas para identificar
    patrones de comportamiento inusuales.
    """
    def __init__(
        self,
        window_size=1,  # Número de pasos temporales en cada ventana
        n_estimators=100,
        contamination='auto',
        max_samples='auto',
        random_state=None,
        features=None  # Lista de nombres de columnas a usar como features
    ):
        self.window_size = window_size
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            bootstrap=False  # bootstrap=False is default in newer versions and often recommended
        )
        self.trained = False
        self.decision_scores_train = []  # Almacena los decision scores de los datos de entrenamiento
        self.features = features if features else ['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']
        self.num_features_per_timestep = len(self.features)
        self.threshold = None  # Umbral para la detección de anomalías

    def _create_windows(self, data_df: pd.DataFrame):
        """
        Crea ventanas deslizantes a partir de un DataFrame de series temporales.
        Cada ventana se aplana para ser una única muestra para Isolation Forest.
        """
        if not isinstance(data_df, pd.DataFrame):
            raise ValueError("data_df debe ser un pandas DataFrame.")
        if data_df.empty or len(data_df) < self.window_size:
            return np.array([])

        # Asegurarse de que solo se usan las columnas especificadas en self.features
        data_for_windows = data_df[self.features].values

        windows = []
        for i in range(len(data_for_windows) - self.window_size + 1):
            window = data_for_windows[i:i + self.window_size, :]
            windows.append(window.flatten())  # Aplanar la ventana
        return np.array(windows).astype(np.float32) if windows else np.array([])

    def fit(self, data_df: pd.DataFrame):
        """
        Entrena el modelo Isolation Forest con el DataFrame de series temporales proporcionado.
        El data_df se convierte en ventanas deslizantes.
        """
        if len(data_df) < self.window_size:
            raise ValueError(
                f"La longitud de la serie de datos ({len(data_df)}) debe ser al menos "
                f"igual al tamaño de la ventana ({self.window_size})."
            )

        windows = self._create_windows(data_df)
        if windows.shape[0] == 0:
            raise ValueError("No hay suficientes datos para crear ventanas de entrenamiento.")

        self.model.fit(windows)

        # Almacenar los decision scores de los datos de entrenamiento para establecer un umbral
        # Los scores más bajos son más anómalos. Usamos el negativo para que scores más altos
        # sean más anómalos.
        self.decision_scores_train = -self.model.decision_function(windows)

        self.trained = True
        print("Entrenamiento del modelo Isolation Forest completado.")

    def get_anomaly_score_for_window(self, window_data_df_slice: pd.DataFrame):
        """
        Calcula el score de anomalía para una única ventana de datos.
        window_data_df_slice: un slice del DataFrame original que representa una ventana.
        """
        if not self.trained:
            raise RuntimeError("El modelo no ha sido entrenado. Llama a fit() primero.")
        if len(window_data_df_slice) != self.window_size:
            raise ValueError(
                f"La longitud de window_data_df_slice ({len(window_data_df_slice)}) debe coincidir "
                f"con el window_size del modelo ({self.window_size})."
            )

        # Asegurarse de que solo se usan las columnas especificadas en self.features
        window_features = window_data_df_slice[self.features].values.flatten().astype(np.float32)
        window_reshaped = window_features.reshape(1, -1)  # IsolationForest espera un array 2D

        # Usamos el negativo del decision_function para que scores más altos indiquen mayor anomalía
        score = -self.model.decision_function(window_reshaped)[0]
        return score

    def is_window_anomalous(self, window_data_df_slice: pd.DataFrame, threshold: float):
        """Determina si una ventana de datos es anómala basándose en un umbral."""
        if self.threshold is None and threshold is None:
            raise ValueError(
                "El umbral no ha sido establecido. "
                "Llama a set_threshold_from_train_data() o provee un umbral."
            )
        current_threshold = threshold if threshold is not None else self.threshold
        score = self.get_anomaly_score_for_window(window_data_df_slice)
        return score > current_threshold

    def detect_anomalies_in_series(self, data_df: pd.DataFrame, threshold: float = None):
        """
        Detecta anomalías en una nueva serie de datos procesándola en ventanas.
        Retorna una lista de tuplas: (índice_ventana, datos_ventana, score, es_anomalia)
        """
        if not self.trained:
            raise RuntimeError("El modelo no ha sido entrenado. Llama a fit() primero.")

        current_threshold = threshold if threshold is not None else self.threshold
        if current_threshold is None:
            raise ValueError("El umbral no ha sido establecido ni provisto.")

        if len(data_df) < self.window_size:
            print("No hay suficientes datos en la serie para formar ventanas.")
            return []

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
        Establece un umbral de anomalía basado en los decision scores de los datos de entrenamiento.
        Un score más alto (después de negar decision_function) indica mayor anomalía.
        """
        if not self.trained or len(self.decision_scores_train) == 0:
            raise RuntimeError(
                "Modelo no entrenado o no hay scores de decisión de entrenamiento disponibles. "
                "Llama a fit() primero."
            )
        self.threshold = np.percentile(self.decision_scores_train, percentile)
        print(
            f"Umbral de anomalía establecido en: {self.threshold:.5f} "
            f"(basado en el percentil {percentile} de los scores de decisión del entrenamiento)"
        )
        return self.threshold


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
    # Añadir algunas anomalías simuladas
    data['close'][20:23] = data['close'][20:23] * 1.2  # Aumento anómalo
    data['tickvol'][50:53] = data['tickvol'][50:53] * 5  # Volumen anómalo
    data['low'][70:73] = data['low'][70:73] * 0.8  # Caída anómala

    data_df = pd.DataFrame(data)
    # Asegurar que 'high' sea siempre >= 'open' y 'close', y 'low' <= 'open' y 'close'
    data_df['high'] = data_df[['open', 'close', 'high']].max(axis=1)
    data_df['low'] = data_df[['open', 'close', 'low']].min(axis=1)

    window_s = 5  # Analizar ventanas de 5 pasos temporales

    # Lista de features a usar por el detector
    features_to_use = ['open', 'high', 'low', 'close', 'tickvol']

    detector = IsolationForestAnomalyDetector(window_size=window_s, features=features_to_use, random_state=42)

    # Entrenar el modelo
    # Para un escenario real, usar un periodo de datos "normales" para el entrenamiento
    print(f"Entrenando Isolation Forest con window_size={window_s}...")
    # Usar una porción de los datos para entrenamiento, simulando datos normales
    train_data_df = data_df.iloc[:80]  # Usar los primeros 80 puntos para entrenar
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

    if not anomalies_info:
        print("No se crearon ventanas para analizar o no se detectaron anomalías.")
    else:
        for i, window, score, is_anom in anomalies_info:
            # window es una lista de listas (window_size x num_features)
            # Para imprimir, podemos mostrar un resumen o las primeras features de la primera fila
            # de la ventana
            first_step_features = ", ".join([f"{val:.2f}" for val in window[0]])
            print(
                f"Ventana desde índice {i} (primer paso: [{first_step_features}, ...]): "
                f"Score={score:.5f} {'<- ANOMALÍA DETECTADA' if is_anom else ''}"
            )
