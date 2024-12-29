import pandas as pd
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split as surprise_train_test_split

class HybridRecommender:
    def __init__(self):
        self.collaborative_model = None
        self.project_features = None
        self.user_preferences = None
        self.max_donation = None

    def load_data(self, interactions_file, projects_file, users_file):
        self.interactions = pd.read_csv(interactions_file)
        self.projects = pd.read_csv(projects_file)
        self.users = pd.read_csv(users_file)

    def preprocess_data(self):
        # Normalize donation amounts to a 0-1 scale
        self.max_donation = self.interactions['donation_amount'].max()
        interactions_normalized = self.interactions.copy()
        interactions_normalized['donation_amount'] = (
            self.interactions['donation_amount'] / self.max_donation
        )

        reader = Reader(rating_scale=(0, 1))
        data = Dataset.load_from_df(
            interactions_normalized[["user_id", "project_id", "donation_amount"]], reader
        )
        return data

    def train_collaborative_model(self, data):
        trainset, _ = surprise_train_test_split(data, test_size=0.2, random_state=42)
        self.collaborative_model = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
        self.collaborative_model.fit(trainset)

    def train_content_based_model(self):
        self.project_features = self.projects.set_index("project_id")["category"].to_dict()
        self.user_preferences = self.interactions.groupby("user_id")["project_id"].apply(list).to_dict()

    def knowledge_based_recommendation(self, user_id):
        user_info = self.users[self.users["user_id"] == user_id].iloc[0]
        user_interests = user_info["interests"]

        recommended_projects = self.projects[self.projects["category"] == user_interests]
        return recommended_projects["project_id"].tolist()

    def hybrid_recommendation(self, user_id):
        if not self.collaborative_model or not self.project_features:
            raise ValueError("Models have not been trained. Please train them before making recommendations.")

        # Get Collaborative Filtering recommendations
        unique_projects = self.interactions["project_id"].unique()
        cf_scores = {
            project_id: self.collaborative_model.predict(user_id, project_id).est * self.max_donation
            for project_id in unique_projects
        }

        # Get Content-Based scores
        user_projects = self.user_preferences.get(user_id, [])
        content_scores = {
            project_id: sum(
                self.project_features[project_id] == self.project_features.get(p, "")
                for p in user_projects
            )
            for project_id in unique_projects
        }

        # Combine scores
        hybrid_scores = {
            project_id: cf_scores.get(project_id, 0) + content_scores.get(project_id, 0)
            for project_id in unique_projects
        }

        # Sort recommendations
        recommended_projects = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        return [project_id for project_id, _ in recommended_projects]
