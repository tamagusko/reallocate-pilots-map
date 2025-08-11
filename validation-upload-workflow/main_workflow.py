#!/usr/bin/env python3
"""
Main workflow script for GeoJSON validation and CKAN upload.

This script orchestrates the complete workflow:
1. Discover and inventory GeoJSON files
2. Run comprehensive validation
3. Generate validation reports
4. Upload validated files to CKAN
5. Generate upload summary reports
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

from geojson_validator import GeoJSONValidator, FileValidationReport
from ckan_uploader import CKANUploader, UploadSummary


class WorkflowOrchestrator:
    """Main workflow orchestration class"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional configuration file"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize components
        self.validator = GeoJSONValidator(self.config.get('validation', {}))
        self.uploader = None  # Initialize lazily when needed
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'validation': {
                'european_bounds': {
                    'min_lon': -31.0, 'max_lon': 45.0,
                    'min_lat': 34.0, 'max_lat': 72.0
                },
                'min_feature_count': 1,
                'max_feature_count': 10000,
                'max_file_size_mb': 100,
                'required_crs': 'EPSG:4326'
            },
            'upload': {
                'organization_id': 'bsc',
                'dataset_prefix': 'reallocate-pilot',
                'resource_formats': ['GeoJSON', 'CSV'],
                'private_datasets': True,
                'auto_create_datasets': True,
                'overwrite_resources': True,
                'only_upload_passed': True,
                'batch_size': 10,
                'retry_attempts': 3,
                'retry_delay': 5,
                'upload_timeout': 300
            },
            'output': {
                'validation_report': 'validation_report.md',
                'upload_report': 'ckan_upload_report.md',
                'summary_json': 'workflow_summary.json',
                'log_file': 'workflow.log'
            },
            'workflow': {
                'data_directory': 'data',
                'backup_enabled': True,
                'backup_directory': 'backup',
                'continue_on_validation_failures': True,
                'continue_on_upload_failures': True
            }
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                self._deep_merge(default_config, file_config)
                # Logger might not be initialized yet, use print for now
                print(f"Loaded configuration from {config_path}")
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to load config file {config_path}: {e}")
                print("Using default configuration.")
        
        return default_config
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_file = self.config['output']['log_file']
        
        # Clear any existing handlers to avoid duplicates
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        root_logger.setLevel(logging.INFO)
        
        # File handler with UTF-8 encoding
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
    
    def discover_files(self, data_dir: Path) -> List[Path]:
        """Discover and inventory all GeoJSON files"""
        self.logger.info(f"Discovering GeoJSON files in {data_dir}")
        
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
        
        geojson_files = list(data_dir.glob("*.geojson"))
        
        if not geojson_files:
            self.logger.warning(f"No GeoJSON files found in {data_dir}")
            return []
        
        self.logger.info(f"Found {len(geojson_files)} GeoJSON files:")
        for file_path in sorted(geojson_files):
            file_size = file_path.stat().st_size
            self.logger.info(f"  - {file_path.name} ({file_size / 1024:.1f} KB)")
        
        return sorted(geojson_files)
    
    def run_validation(self, data_dir: Path) -> List[FileValidationReport]:
        """Run comprehensive validation on all files"""
        self.logger.info("="*60)
        self.logger.info("STARTING VALIDATION PHASE")
        self.logger.info("="*60)
        
        validation_reports = self.validator.validate_all_files(data_dir)
        
        # Calculate validation summary statistics
        total_files = len(validation_reports)
        passed_files = sum(1 for r in validation_reports if r.overall_status == "PASS")
        failed_files = total_files - passed_files
        
        self.logger.info("="*60)
        self.logger.info("VALIDATION PHASE COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Passed validation: {passed_files}")
        self.logger.info(f"Failed validation: {failed_files}")
        self.logger.info(f"Success rate: {(passed_files/total_files)*100:.1f}%")
        
        # Log files with majority failed tests
        critical_failures = [r for r in validation_reports if r.failed_tests > r.passed_tests]
        if critical_failures:
            self.logger.warning(f"Files with majority failed tests: {len(critical_failures)}")
            for report in critical_failures:
                self.logger.warning(f"  - {report.filename}: {report.failed_tests}/{report.total_tests} failed")
        
        return validation_reports
    
    def run_upload(self, data_dir: Path, validation_reports: List[FileValidationReport]) -> Optional[UploadSummary]:
        """Run CKAN upload for validated files"""
        self.logger.info("="*60)
        self.logger.info("STARTING UPLOAD PHASE")
        self.logger.info("="*60)
        
        try:
            # Initialize uploader (only when needed)
            if self.uploader is None:
                self.uploader = CKANUploader(self.config.get('upload', {}))
            
            # Filter files based on configuration
            only_passed = self.config['upload']['only_upload_passed']
            upload_summary = self.uploader.upload_validated_files(
                data_dir, validation_reports, only_passed=only_passed
            )
            
            self.logger.info("="*60)
            self.logger.info("UPLOAD PHASE COMPLETE")
            self.logger.info("="*60)
            self.logger.info(f"Total files processed: {upload_summary.total_files}")
            self.logger.info(f"Successful uploads: {upload_summary.successful_uploads}")
            self.logger.info(f"Failed uploads: {upload_summary.failed_uploads}")
            self.logger.info(f"Upload success rate: {upload_summary.success_rate*100:.1f}%")
            self.logger.info(f"Total upload time: {upload_summary.total_upload_time:.2f} seconds")
            
            return upload_summary
            
        except Exception as e:
            self.logger.error(f"Upload phase failed: {str(e)}")
            if not self.config['workflow']['continue_on_upload_failures']:
                raise
            return None
    
    def generate_reports(self, validation_reports: List[FileValidationReport], 
                        upload_summary: Optional[UploadSummary] = None) -> Dict[str, str]:
        """Generate comprehensive reports"""
        self.logger.info("Generating reports...")
        
        report_files = {}
        
        # Validation report
        validation_report_path = Path(self.config['output']['validation_report'])
        report_files['validation'] = self.validator.generate_validation_report(
            validation_reports, validation_report_path
        )
        
        # Upload report
        if upload_summary and self.uploader:
            upload_report_path = Path(self.config['output']['upload_report'])
            report_files['upload'] = self.uploader.generate_upload_report(
                upload_summary, upload_report_path
            )
        
        # Workflow summary JSON
        summary_data = {
            'workflow': {
                'timestamp': datetime.now().isoformat(),
                'config': self.config,
                'data_directory': str(self.config['workflow']['data_directory'])
            },
            'validation': {
                'total_files': len(validation_reports),
                'passed_files': sum(1 for r in validation_reports if r.overall_status == "PASS"),
                'failed_files': sum(1 for r in validation_reports if r.overall_status == "FAIL"),
                'files': [
                    {
                        'filename': r.filename,
                        'city': r.city_name,
                        'pilot': r.pilot_number,
                        'status': r.overall_status,
                        'success_rate': r.success_rate,
                        'file_size': r.file_size,
                        'processing_time': r.processing_time
                    }
                    for r in validation_reports
                ]
            }
        }
        
        if upload_summary:
            summary_data['upload'] = {
                'total_files': upload_summary.total_files,
                'successful_uploads': upload_summary.successful_uploads,
                'failed_uploads': upload_summary.failed_uploads,
                'success_rate': upload_summary.success_rate,
                'total_upload_time': upload_summary.total_upload_time,
                'ckan_url': self.uploader.ckan_url if self.uploader else None,
                'files': [
                    {
                        'filename': r.filename,
                        'success': r.success,
                        'dataset_id': r.dataset_id,
                        'resource_id': r.resource_id,
                        'upload_time': r.upload_time,
                        'message': r.message
                    }
                    for r in upload_summary.upload_results
                ]
            }
        
        summary_json_path = Path(self.config['output']['summary_json'])
        with open(summary_json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        report_files['summary'] = str(summary_json_path)
        
        self.logger.info(f"Reports generated:")
        for report_type, file_path in report_files.items():
            self.logger.info(f"  - {report_type.title()}: {file_path}")
        
        return report_files
    
    def run_complete_workflow(self, data_dir: Path, skip_upload: bool = False) -> Dict[str, any]:
        """Run the complete validation and upload workflow"""
        workflow_start = datetime.now()
        
        self.logger.info("="*80)
        self.logger.info("REALLOCATE GEOJSON VALIDATION & CKAN UPLOAD WORKFLOW")
        self.logger.info("="*80)
        self.logger.info(f"Started: {workflow_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Data directory: {data_dir}")
        self.logger.info(f"Skip upload: {skip_upload}")
        
        try:
            # Phase 1: File discovery
            files = self.discover_files(data_dir)
            if not files:
                self.logger.warning("No files to process. Workflow complete.")
                return {'status': 'completed', 'message': 'No files found'}
            
            # Phase 2: Validation
            validation_reports = self.run_validation(data_dir)
            
            if not validation_reports:
                self.logger.error("Validation failed to produce any reports")
                return {'status': 'failed', 'message': 'Validation phase failed'}
            
            # Check if we should continue with upload
            passed_validation = sum(1 for r in validation_reports if r.overall_status == "PASS")
            if passed_validation == 0 and not self.config['workflow']['continue_on_validation_failures']:
                self.logger.error("No files passed validation and continue_on_validation_failures is False")
                return {'status': 'failed', 'message': 'No files passed validation'}
            
            # Phase 3: Upload (if not skipped)
            upload_summary = None
            if not skip_upload:
                upload_summary = self.run_upload(data_dir, validation_reports)
            else:
                self.logger.info("Upload phase skipped as requested")
            
            # Phase 4: Report generation
            report_files = self.generate_reports(validation_reports, upload_summary)
            
            # Workflow summary
            workflow_end = datetime.now()
            total_time = (workflow_end - workflow_start).total_seconds()
            
            self.logger.info("="*80)
            self.logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
            self.logger.info("="*80)
            self.logger.info(f"Total processing time: {total_time:.2f} seconds")
            self.logger.info(f"Files processed: {len(validation_reports)}")
            
            if validation_reports:
                passed = sum(1 for r in validation_reports if r.overall_status == "PASS")
                self.logger.info(f"Validation success: {passed}/{len(validation_reports)}")
            
            if upload_summary:
                self.logger.info(f"Upload success: {upload_summary.successful_uploads}/{upload_summary.total_files}")
            
            return {
                'status': 'completed',
                'total_time': total_time,
                'files_processed': len(validation_reports),
                'validation_reports': validation_reports,
                'upload_summary': upload_summary,
                'report_files': report_files
            }
            
        except Exception as e:
            self.logger.error(f"Workflow failed with error: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e),
                'message': 'Workflow terminated due to unexpected error'
            }


def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(
        description="GeoJSON validation and CKAN upload workflow for REALLOCATE living labs data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete workflow (validation + upload)
  python main_workflow.py

  # Run only validation (skip upload)
  python main_workflow.py --validation-only

  # Use custom data directory
  python main_workflow.py --data-dir /path/to/data

  # Use custom configuration
  python main_workflow.py --config config.json

  # Verbose logging
  python main_workflow.py --verbose
        """
    )
    
    parser.add_argument(
        '--data-dir', 
        type=Path, 
        default=Path('data'),
        help='Directory containing GeoJSON files (default: data)'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration JSON file'
    )
    
    parser.add_argument(
        '--validation-only',
        action='store_true',
        help='Run validation only, skip CKAN upload'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run validation and generate upload plan without actual upload'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator(args.config)
        
        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Determine if we should skip upload
        skip_upload = args.validation_only or args.dry_run
        
        # Run workflow
        result = orchestrator.run_complete_workflow(args.data_dir, skip_upload=skip_upload)
        
        # Exit with appropriate code
        if result['status'] == 'completed':
            print(f"\n✅ Workflow completed successfully!")
            if 'report_files' in result:
                print("📄 Generated reports:")
                for report_type, file_path in result['report_files'].items():
                    print(f"   - {report_type.title()}: {file_path}")
            sys.exit(0)
        else:
            print(f"\n❌ Workflow failed: {result.get('message', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Workflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()