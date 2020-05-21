import logging

import pytest

logger = logging.getLogger('streamsets.ci_cd_poc')


def pytest_addoption(parser):
    parser.addoption('--pipeline-id')
    parser.addoption('--upgrade-jobs', action='store_true')
    parser.addoption('--environment')
    parser.addoption('--pipeline_version')


@pytest.fixture(scope='session')
def sch(sch_session):
    yield sch_session


@pytest.fixture(scope='session')
def pipeline(sch, request):
    pipeline_id = request.config.getoption('pipeline_id')
    pipeline_ = sch.pipelines.get(pipeline_id=pipeline_id)
    environment = request.config.getoption('environment')
    pipeline_version = request.config.getoption('pipeline_version')

    yield pipeline_

    jobs_to_delete = sch.jobs.get_all(pipeline_id=pipeline_.pipeline_id, description='CI/CD test job')
    if jobs_to_delete:
        logger.debug('Deleting test jobs: %s ...', ', '.join(str(job) for job in jobs_to_delete))
        sch.delete_job(*jobs_to_delete)

    if not request.session.testsfailed:
        if request.config.getoption('upgrade_jobs'):

            logger.info("environment: " + environment)
            logger.info("pipeline_version:" + pipeline_version)

            pipeline_ = sch.pipelines.get(pipeline_id=pipeline_id)
            jobs_to_upgrade = [job for job in sch.jobs.get_all(pipeline_id=pipeline_id)
                               if (job.pipeline_commit_label != f'v{pipeline_.version}'
                                   and job.job_name.startswith(environment))]
            logger.info('list of jobs to upgrade: %s', ', '.join(str(job) for job in jobs_to_upgrade))
            if jobs_to_upgrade and pipeline_version == 'LATEST':
                logger.info('Upgrading jobs: %s ...', ', '.join(str(job) for job in jobs_to_upgrade))
                sch.upgrade_job(*jobs_to_upgrade)
            elif jobs_to_upgrade and pipeline_version != 'LATEST':
                pipeline_commit = pipeline_.commits.get(version=pipeline_version)

                logger.info('Upgrading jobs with older version: %s ...', ', '.join(str(job) for job in jobs_to_upgrade))
                for job in jobs_to_upgrade:
                    job.commit = pipeline_commit
                    sch.update_job(job)

            else:
                logger.warning('No jobs need to be upgraded')

