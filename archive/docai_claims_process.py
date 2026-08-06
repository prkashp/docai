from airflow.models import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta
import pendulum

local_tz = pendulum.timezone("US/Eastern")

# These args are used for each task
# max time allowed for the execution of this task instance,
# if it goes beyond it will raise an exception and fail.

args = {
    'owner': 'Data Engineers',
    'email': ['prakashpro86@gmail.com'],
    'email_on_failure': True,
    'start_date': datetime(2024, 12, 23, tzinfo=local_tz),
    'retries': 2,
    'email_on_retry': True,
    'retry_delay': timedelta(minutes=10),
    'execution_timeout': timedelta(minutes=120)
}

schedule = '40 10 * * *'  # 10:40 PM EST (Files arrive at 10:40 PM EST)
name='docai_eldorado_claims_process'

# Set this to False to run all tasks normally
SKIP_ALL_TASKS = True

dag = DAG(
    name,
    default_args=args,
    schedule_interval=schedule,
    dagrun_timeout=timedelta(minutes=360),
    catchup=False
)

# Create a dummy task that will be the only task that runs when skipping all tasks
dummy_start = DummyOperator(
    task_id='dummy_start',
    dag=dag
)

dummy_end = DummyOperator(
    task_id='dummy_end',
    dag=dag
)

unzip_raw_claims = BashOperator(
    task_id='unzip_raw_claims',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/preprocessor/unzipper.py {{batch_environment}}
    """,
    dag=dag)

call_preprocessor_model = BashOperator(
    task_id='call_preprocessor_model',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/preprocessor/preprocessor_model.py {{batch_environment}}
    """,
    dag=dag)

classify_files = BashOperator(
    task_id='classify_files',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/preprocessor/classifier.py {{batch_environment}}
    """,
    dag=dag)

call_dental_predict = BashOperator(
    task_id='call_dental_predict',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/core/dental_claims_model.py {{batch_environment}}
    """,
    dag=dag)

# python $SCRIPTDIR/docai/eldorado/core/professional_claims_model.py {{batch_environment}}
call_professional_predict = BashOperator(
    task_id='call_professional_predict',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    echo "Skip"
    """,
    dag=dag)
# python $SCRIPTDIR/docai/eldorado/core/institutional_claims_model.py {{batch_environment}}
call_institutional_predict = BashOperator(
    task_id='call_institutional_predict',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    echo "Skip"
    """,
    dag=dag)

postprocessor = BashOperator(
    task_id='postprocessor',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/postprocessor/postprocessor.py -env={{batch_environment}}
    """,
    dag=dag)

json_to_x12_dental_conversion = BashOperator(
    task_id='json_to_x12_dental_conversion',
    bash_command="""
    SCRIPTDIR="$HOME/837"
    python $SCRIPTDIR/docai/eldorado/postprocessor/dental/s3_to_edi.py {{batch_environment}}
    """,
    dag=dag)

# Set up task dependencies based on SKIP_ALL_TASKS flag
if SKIP_ALL_TASKS:
    # If skipping all tasks, just run the dummy tasks
    dummy_end.set_upstream(dummy_start)
else:
    # Normal task dependencies when not skipping
    call_preprocessor_model.set_upstream(unzip_raw_claims)
    classify_files.set_upstream(call_preprocessor_model)
    call_dental_predict.set_upstream(classify_files)
    call_professional_predict.set_upstream(classify_files)
    call_institutional_predict.set_upstream(classify_files)
    postprocessor.set_upstream([call_professional_predict, call_institutional_predict, call_dental_predict])
    json_to_x12_dental_conversion.set_upstream(postprocessor)
