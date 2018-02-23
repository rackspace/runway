"""The gen-sample command."""
from .base import Base


class GenSample(Base):
    """Extend Base with execute to run the module generators."""

    def execute(self):
        """Run selected module generator."""
        if self.options['cfn']:
            self.generate_sample_cfn_module()
        elif self.options['sls']:
            self.generate_sample_sls_module()
        elif self.options['stacker']:
            self.generate_sample_stacker_module()
        elif self.options['tf']:
            self.generate_sample_tf_module()
