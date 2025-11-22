declare namespace Api {
  namespace Iteration {
    interface LeaderDashboardItem extends IterationItem {
      product_id: number
    }

    interface ProjectDashboardItem {
      iteration_name: string
      story_points: number
      completed_story_points: number
    }

    interface IterationItem {
      id: string
      name: string
      code: string
      start_date: string
      end_date: string
      is_current: boolean
      product_name: string
      product_code: string
      pm: string
      latest_metric: {
        id: string
        iteration: string
        total_requirements: number
        completed_requirements: number
        total_workload: string
        completed_workload: string
        grade_a_count: number
        grade_c_count: number
        need_decompose_count: number
        not_decomposed_count: number
        no_need_decompose_count: number
        orphan_count: number
        refresh_date: string
        completion_rate: number
        grade_a_rate: number
        grade_ac_rate: number
        decompose_rate: number
        orphan_rate: number
      }
    }
  }
}
