#!/usr/bin/env python3
"""
Modélisation de base de données pour la feedback loop
Suite à la validation de la vésion d'évaluation, passer à une version en production
"""

from dataclasses import dataclass
from datetime import datetime
import sqlite3
import json
from typing import List, Optional


FEEDBACK_LOOP_SCHEMA_NOTES = """
Base de donnees Feedback Loop
============================

Tables principales:
- feedbacks: Stocke tous les feedbacks utilisateur

Champs:
- id: Cle primaire (auto-increment)
- image_filename: Nom original du fichier
- image_data_url: Image encodee en base64 pour stockage/retraitement
- predicted_label: Classe predite par le modele
- user_label: Classe choisie par l'utilisateur
- confidence_score: Score de confiance de la prediction
- timestamp: Date/heure du feedback
- is_correct: Booleen (predicted == user)
- model_version: Version du modele utilise

Index:
- idx_timestamp: Ameliore les requetes temporelles
- idx_is_correct: Ameliore les statistiques
"""


@dataclass
class Feedback:
    """Modèle de données pour un feedback utilisateur."""
    id: Optional[int] = None
    image_filename: str = ""
    image_data_url: str = ""  # Pour stockage temporaire
    predicted_label: str = ""
    user_label: str = ""
    confidence_score: float = 0.0
    timestamp: Optional[datetime] = None
    is_correct: bool = False  # True si user_label == predicted_label
    model_version: str = "1.0"

    def __post_init__(self):
        """Initialise les champs après création."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        self.is_correct = (self.predicted_label == self.user_label)


class FeedbackDatabase:
    """Gestionnaire de base de données pour les feedbacks utilisateur."""

    def __init__(self, db_path: str = "app.db"):
        """
        Initialise la connexion à la base de données SQLite.

        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path
        self.connection = None
        self._create_tables()

    def _create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_filename TEXT,
                    image_data_url TEXT,
                    predicted_label TEXT,
                    user_label TEXT,
                    confidence_score REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_correct BOOLEAN,
                    model_version TEXT
                )
            ''')

            # Index pour améliorer les performances
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON feedbacks (timestamp DESC)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_correct
                ON feedbacks (is_correct)
            ''')

    def save_feedback(self, feedback: Feedback) -> bool:
        """
        Sauvegarde un feedback dans la base de données.

        Args:
            feedback: Feedback à sauvegarder

        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO feedbacks
                    (image_filename, image_data_url, predicted_label,
                     user_label, confidence_score, is_correct, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback.image_filename,
                    feedback.image_data_url,
                    feedback.predicted_label,
                    feedback.user_label,
                    feedback.confidence_score,
                    feedback.is_correct,
                    feedback.model_version
                ))

                # Récupérer l'ID généré
                feedback.id = cursor.lastrowid
                conn.commit()

                print(f"Feedback sauvegardé avec ID: {feedback.id}")
                return True

        except sqlite3.Error as e:
            print(f"Erreur lors de la sauvegarde du feedback: {e}")
            return False

    def get_feedbacks(self, limit: int = 50) -> List[Feedback]:
        """
        Récupère les derniers feedbacks.

        Args:
            limit: Nombre maximum de feedbacks à récupérer

        Returns:
            Liste des feedbacks
        """
        feedbacks = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, image_filename, image_data_url, predicted_label,
                           user_label, confidence_score, timestamp, is_correct, model_version
                    FROM feedbacks
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

                for row in cursor.fetchall():
                    feedback = Feedback(
                        id=row[0],
                        image_filename=row[1],
                        image_data_url=row[2],
                        predicted_label=row[3],
                        user_label=row[4],
                        confidence_score=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        is_correct=bool(row[7]),
                        model_version=row[8]
                    )
                    feedbacks.append(feedback)

        except (sqlite3.Error, ValueError) as e:
            print(f"Erreur lors de la récupération des feedbacks: {e}")

        return feedbacks

    def get_statistics(self) -> dict:
        """
        Calcule des statistiques sur les feedbacks.

        Returns:
            Dictionnaire avec les statistiques
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Nombre total de feedbacks
                cursor.execute('SELECT COUNT(*) FROM feedbacks')
                total_feedbacks = cursor.fetchone()[0]

                # Pourcentage de bonnes prédictions
                cursor.execute('SELECT COUNT(*) FROM feedbacks WHERE is_correct = 1')
                correct_predictions = cursor.fetchone()[0]

                # Distribution des classes prédites
                cursor.execute('''
                    SELECT predicted_label, COUNT(*) as count
                    FROM feedbacks
                    GROUP BY predicted_label
                ''')
                predicted_distribution = cursor.fetchall()

                # Distribution des classes utilisateur
                cursor.execute('''
                    SELECT user_label, COUNT(*) as count
                    FROM feedbacks
                    GROUP BY user_label
                ''')
                user_distribution = cursor.fetchall()

                accuracy = (correct_predictions / total_feedbacks * 100) if total_feedbacks > 0 else 0

                return {
                    'total_feedbacks': total_feedbacks,
                    'accuracy': round(accuracy, 2),
                    'correct_predictions': correct_predictions,
                    'predicted_distribution': dict(predicted_distribution),
                    'user_distribution': dict(user_distribution)
                }

        except sqlite3.Error as e:
            print(f"Erreur lors du calcul des statistiques: {e}")
            return {}

    def export_for_retraining(self, filename: str = "retraining_data.json"):
        """
        Exporte les données pour le réentraînement du modèle.

        Args:
            filename: Nom du fichier d'export

        Returns:
            True si l'export a réussi, False sinon
        """
        try:
            feedbacks = self.get_feedbacks(limit=10000)  # Tous les feedbacks

            # Préparer les données pour l'export
            export_data = []
            for feedback in feedbacks:
                export_data.append({
                    'image_data_url': feedback.image_data_url,
                    'true_label': feedback.user_label,
                    'predicted_label': feedback.predicted_label,
                    'confidence': feedback.confidence_score,
                    'timestamp': feedback.timestamp.isoformat() if feedback.timestamp else None
                })

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)

            print(f"Données exportées vers {filename}")
            return True

        except (OSError, sqlite3.Error) as e:
            print(f"Erreur lors de l'export: {e}")
            return False

    def close(self):
        """Ferme la connexion à la base de données."""
        if self.connection:
            self.connection.close()


if __name__ == "__main__":
    # Exemple d'utilisation
    db = FeedbackDatabase()
    print("Base de données créée avec succès!")

    # Afficher les statistiques actuelles
    stats = db.get_statistics()
    print("Statistiques actuelles:", stats)
