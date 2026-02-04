from datetime import datetime
from . import db

class DiagramCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repo_url = db.Column(db.String(512), nullable=False)
    diagram_type = db.Column(db.String(50), nullable=False, default='flowchart')
    diagram_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('repo_url', 'diagram_type', name='_repo_type_uc'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "diagram_type": self.diagram_type,
            "diagram_content": self.diagram_content,
            "created_at": self.created_at.isoformat()
        }
