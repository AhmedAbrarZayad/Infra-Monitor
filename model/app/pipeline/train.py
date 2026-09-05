from sklearn.ensemble import IsolationForest


def train_model(matrix, *, contamination):
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(matrix)
    return model
